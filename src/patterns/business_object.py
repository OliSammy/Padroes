"""
Padrão Business Object para encapsular lógica de negócio
Orquestra os padrões GoF e gerencia as regras de negócio
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database.config import get_db
from database.crud import (
    ClienteRepository, BebidaRepository, PersonalizacaoRepository,
    CarrinhoRepository, PedidoRepository
)
from database.models import (
    StatusPedidoEnum, MetodoPagamentoEnum,
    TipoBebidasEnum, Cliente, Bebida, Pedido, ItemCarrinho
)
from .decorator import ComponenteBebida, BebidaPersonalizada, LeiteDeAveia, LeiteDesnatado, Canela, ChocolateExtra, Chantilly, SemAcucar
from .factory import MenuFactory, BebidaFactorySelector
from .strategy import ContextoPagamento, DescontoPix, DescontoFidelidade, SemDesconto
from .observer import PedidoSubject, CozinhaObserver, ClienteObserver
from .state import Pedido as EstadoPedido
from .command import CommandInvoker, CriarPedidoCommand, AlterarStatusPedidoCommand


class StrategySelector:
    """Selector para escolher estratégia de desconto baseada apenas no método de pagamento"""
    
    @staticmethod
    def criar_strategy(metodo_pagamento: MetodoPagamentoEnum):
        """Cria strategy baseada no método de pagamento com desconto automático"""
        if metodo_pagamento == MetodoPagamentoEnum.PIX:
            return DescontoPix()
        elif metodo_pagamento == MetodoPagamentoEnum.FIDELIDADE:
            return DescontoFidelidade()
        else:
            return SemDesconto()


class ContextoPedido:
    """Contexto para gerenciar estados do pedido"""
    
    def __init__(self):
        self.pedido_id = None
        self.status_atual = None
    
    def set_pedido_id(self, pedido_id: int):
        self.pedido_id = pedido_id
    
    def set_status(self, status: StatusPedidoEnum):
        self.status_atual = status
    
    def pode_transicionar_para(self, novo_status: StatusPedidoEnum) -> bool:
        """Verifica se pode transicionar para o novo status"""
        transicoes_permitidas = {
            StatusPedidoEnum.PENDENTE: [StatusPedidoEnum.RECEBIDO, StatusPedidoEnum.CANCELADO],
            StatusPedidoEnum.RECEBIDO: [StatusPedidoEnum.EM_PREPARO, StatusPedidoEnum.CANCELADO],
            StatusPedidoEnum.EM_PREPARO: [StatusPedidoEnum.PRONTO],
            StatusPedidoEnum.PRONTO: [StatusPedidoEnum.ENTREGUE],
            StatusPedidoEnum.ENTREGUE: [],
            StatusPedidoEnum.CANCELADO: []
        }
        
        if self.status_atual in transicoes_permitidas:
            return novo_status in transicoes_permitidas[self.status_atual]
        return False


class PedidoBO:
    def _cancelar_pedido_state_pattern_impl(self, pedido_id: int) -> dict:
        """Implementação original do cancelamento para uso interno do Command"""
        from fastapi import HTTPException, status
        from database.models import StatusPedidoEnum
        from patterns.state import Pedido as PedidoState
        from patterns.observer import PedidoSubject, CozinhaObserver, ClienteObserver

        pedido_repo = PedidoRepository(self.db)
        pedido_db = pedido_repo.get_by_id(pedido_id)
        if not pedido_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido não encontrado"
            )

        pedido_state = PedidoState(pedido_id, pedido_db.status.value)
        pode_cancelar, estado_anterior, _ = pedido_state.cancelar_pedido()

        if not pode_cancelar:
            estado_atual = pedido_state.get_estado_display()
            razoes = {
                "Em preparo": "Pedido já está sendo preparado na cozinha",
                "Pronto": "Pedido já está pronto para entrega",
                "Entregue": "Pedido já foi entregue ao cliente",
                "Cancelado": "Pedido já está cancelado"
            }
            razao = razoes.get(estado_atual, "Estado não permite cancelamento")
            return {
                "success": False,
                "pedido_id": pedido_id,
                "estado_atual": estado_atual,
                "message": f"Não é possível cancelar pedido no estado '{estado_atual}'",
                "razao": razao,
                "estados_que_permitem_cancelamento": ["Pendente", "Recebido"]
            }

        # Atualizar no banco de dados
        pedido_repo.update_status(pedido_id, StatusPedidoEnum.CANCELADO)

        # Usar Observer Pattern para notificar cancelamento
        subject = PedidoSubject(pedido_id)
        subject.adicionar_observer(CozinhaObserver())
        subject.adicionar_observer(ClienteObserver())
        subject.notificar_observers()

        return {
            "success": True,
            "pedido_id": pedido_id,
            "estado_anterior": estado_anterior,
            "novo_estado": "Cancelado",
            "message": f"Pedido cancelado com sucesso usando State Pattern. Estado anterior: '{estado_anterior}'",
            "padroes_utilizados": ["State Pattern", "Observer Pattern"]
        }

    def _avancar_estado_pedido_impl(self, pedido_id: int) -> dict:
        """Implementação original do avanço de estado para uso interno do Command"""
        # Buscar pedido no banco
        pedido_repo = PedidoRepository(self.db)
        pedido_db = pedido_repo.get_by_id(pedido_id)
        if not pedido_db:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido não encontrado"
            )

        # Criar instância do State Pattern com estado atual
        from patterns.state import Pedido as PedidoState
        pedido_state = PedidoState(pedido_id, pedido_db.status.value)
        estado_atual = pedido_state.get_estado_display()

        # Verificar se pode avançar (não está em estado final)
        if estado_atual in ["Entregue", "Cancelado"]:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não é possível avançar estado. Pedido está '{estado_atual}' (estado final)"
            )

        # Usar State Pattern para avançar
        estado_anterior, novo_estado = pedido_state.avancar_estado()

        # Converter para formato do banco
        from database.models import StatusPedidoEnum
        status_map = {
            "Pendente": StatusPedidoEnum.PENDENTE,
            "Recebido": StatusPedidoEnum.RECEBIDO,
            "Em preparo": StatusPedidoEnum.EM_PREPARO,
            "Pronto": StatusPedidoEnum.PRONTO,
            "Entregue": StatusPedidoEnum.ENTREGUE
        }
        novo_status_db = status_map.get(novo_estado)
        if not novo_status_db:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado '{novo_estado}' não é válido"
            )

        # Atualizar no banco de dados
        pedido_repo.update_status(pedido_id, novo_status_db)

        # Usar Observer Pattern para notificar
        from patterns.observer import PedidoSubject, CozinhaObserver, ClienteObserver
        subject = PedidoSubject(pedido_id)
        subject.adicionar_observer(CozinhaObserver())
        subject.adicionar_observer(ClienteObserver())
        subject.notificar_observers()

        # Proxima transição
        transicoes = {
            "Pendente": "Recebido",
            "Recebido": "Em preparo",
            "Em preparo": "Pronto",
            "Pronto": "Entregue",
            "Entregue": None,
            "Cancelado": None
        }
        proxima_transicao = transicoes.get(novo_estado)

        return {
            "success": True,
            "pedido_id": pedido_id,
            "estado_anterior": estado_anterior,
            "novo_estado": novo_estado,
            "message": f"Estado avançado de '{estado_anterior}' para '{novo_estado}'.",
            "proxima_transicao": proxima_transicao
        }
    def obter_notificacoes_dict(self, current_user, tipo: str = '', limit: int = 20) -> list:
        """Retorna notificações do usuário (cliente ou staff) como lista de dicts serializáveis"""
        from database.crud import PedidoRepository
        from datetime import datetime
        notificacoes_usuario = []
        # Staff
        if hasattr(current_user, 'tipo_usuario') and getattr(current_user.tipo_usuario, 'value', None) == "staff":
            notificacoes_usuario = [
                {
                    "id": "1",
                    "tipo": "novo_pedido",
                    "titulo": "Novo Pedido",
                    "mensagem": f"Novo pedido recebido do cliente {getattr(current_user, 'nome', '')}",
                    "timestamp": datetime.now(),
                    "lida": False,
                    "dados_extras": {"urgente": False}
                },
                {
                    "id": "2",
                    "tipo": "pedido_atrasado",
                    "titulo": "Pedido Atrasado",
                    "mensagem": "Pedido #123 está há mais de 15 minutos aguardando",
                    "timestamp": datetime.now(),
                    "lida": False,
                    "dados_extras": {"pedido_id": 123, "tempo_espera": 15}
                }
            ]
        else:
            # Cliente vê notificações específicas dele
            db = getattr(self, 'db', None)
            cliente_id = getattr(current_user, 'id', None)
            if db is not None and isinstance(cliente_id, int):
                pedido_repo = PedidoRepository(db)
                pedidos_recentes = pedido_repo.get_by_cliente(cliente_id)[:3]
                notificacoes_usuario = [
                    {
                        "id": f"pedido_{getattr(p, 'id', '')}",
                        "tipo": "status_pedido",
                        "titulo": "Status do Pedido",
                        "mensagem": f"Seu pedido #{getattr(p, 'id', '')} está {getattr(getattr(p, 'status', None), 'value', '')}",
                        "timestamp": getattr(p, 'updated_at', None),
                        "lida": False,
                        "dados_extras": {"pedido_id": getattr(p, 'id', ''), "status": getattr(getattr(p, 'status', None), 'value', '')}
                    } for p in pedidos_recentes
                ]
        # Filtrar por tipo se fornecido
        if tipo:
            notificacoes_usuario = [n for n in notificacoes_usuario if n["tipo"] == tipo]
        return notificacoes_usuario[:limit]
    def historico_geral_dict(self, status_filtro: Optional[str] = None, data_inicio: Optional[datetime] = None, data_fim: Optional[datetime] = None, limit: int = 50, offset: int = 0) -> list:
        """Retorna histórico geral de pedidos com filtros como lista de dicts serializáveis"""
        from database.crud import PedidoRepository, HistoricoRepository
        from database.models import StatusPedidoEnum
        status_enum = None
        if status_filtro:
            try:
                status_enum = StatusPedidoEnum(status_filtro)
            except Exception:
                status_enum = None
        pedidos = PedidoRepository(self.db).listar_com_filtros(
            status=status_enum,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limit=limit,
            offset=offset
        )
        resultado = []
        for pedido in pedidos:
            def is_column(val):
                return hasattr(val, '__class__') and 'sqlalchemy' in str(type(val))
            d = {}
            pedido_id = getattr(pedido, "id", None)
            if pedido_id is None or is_column(pedido_id):
                continue
            d["pedido_id"] = pedido_id
            status_atual = getattr(pedido, "status", None)
            d["status_atual"] = status_atual.value if status_atual and hasattr(status_atual, "value") else (str(status_atual) if status_atual and not is_column(status_atual) else None)
            cliente = getattr(pedido, "cliente", None)
            d["cliente_nome"] = getattr(cliente, "nome", None) if cliente and not is_column(cliente) else None
            val = getattr(pedido, "total_final", None)
            d["total_final"] = float(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) else None
            val = getattr(pedido, "created_at", None)
            d["created_at"] = val if val is not None and not is_column(val) else None
            # Histórico detalhado
            historico = HistoricoRepository(self.db).obter_por_pedido(pedido_id)
            hist_list = []
            for h in historico:
                hist_dict = {}
                status_ant = getattr(h, "status_anterior", None)
                hist_dict["status_anterior"] = status_ant.value if status_ant and hasattr(status_ant, "value") else (str(status_ant) if status_ant and not is_column(status_ant) else None)
                status_novo = getattr(h, "status_novo", None)
                hist_dict["status_novo"] = status_novo.value if status_novo and hasattr(status_novo, "value") else (str(status_novo) if status_novo and not is_column(status_novo) else None)
                hist_dict["observacao"] = str(getattr(h, "observacao", None)) if getattr(h, "observacao", None) is not None and not is_column(getattr(h, "observacao", None)) else None
                hist_dict["timestamp"] = getattr(h, "timestamp", None) if getattr(h, "timestamp", None) is not None and not is_column(getattr(h, "timestamp", None)) else None
                hist_list.append(hist_dict)
            d["historico"] = hist_list
            resultado.append(d)
        return resultado
    def historico_pedido_dict(self, pedido_id: int) -> list:
        """Retorna o histórico de um pedido como lista de dicts serializáveis, robusto para Column/None"""
        from database.crud import HistoricoRepository, PedidoRepository
        pedido = PedidoRepository(self.db).obter_por_id(pedido_id)
        if not pedido:
            return []
        historico = HistoricoRepository(self.db).obter_por_pedido(pedido_id)
        resultado = []
        for h in historico:
            def is_column(val):
                return hasattr(val, '__class__') and 'sqlalchemy' in str(type(val))
            d = {}
            d["id"] = getattr(h, "id", None) if not is_column(getattr(h, "id", None)) else None
            d["pedido_id"] = getattr(h, "pedido_id", None) if not is_column(getattr(h, "pedido_id", None)) else None
            status_ant = getattr(h, "status_anterior", None)
            d["status_anterior"] = status_ant.value if status_ant and hasattr(status_ant, "value") else (str(status_ant) if status_ant and not is_column(status_ant) else None)
            status_novo = getattr(h, "status_novo", None)
            d["status_novo"] = status_novo.value if status_novo and hasattr(status_novo, "value") else (str(status_novo) if status_novo and not is_column(status_novo) else None)
            obs = getattr(h, "observacao", None)
            d["observacao"] = str(obs) if obs is not None and not is_column(obs) else None
            ts = getattr(h, "timestamp", None)
            d["timestamp"] = ts if ts is not None and not is_column(ts) else None
            resultado.append(d)
        return resultado
    def estatisticas_dict(self) -> dict:
        """Retorna estatísticas gerais do sistema como dict serializável"""
        estatisticas = self.obter_estatisticas()
        total_pedidos = estatisticas.get("total_pedidos", 0)
        faturamento_total = estatisticas.get("faturamento_total", 0.0)
        ticket_medio = faturamento_total / total_pedidos if total_pedidos > 0 else 0.0
        return {
            "total_pedidos": total_pedidos,
            "pedidos_hoje": estatisticas.get("pedidos_hoje", 0),
            "faturamento_total": faturamento_total,
            "pedidos_pendentes": estatisticas.get("pedidos_pendentes", 0),
            "pedidos_em_preparo": estatisticas.get("pedidos_em_preparo", 0),
            "ticket_medio": ticket_medio
        }

    def bebidas_mais_vendidas_dict(self, limite: int, dias: int) -> list:
        """Retorna lista de bebidas mais vendidas como dicts serializáveis"""
        from sqlalchemy import func, desc
        from database.models import Pedido, Bebida, ItemPedido, StatusPedidoEnum
        from database.config import get_db
        db = self.db
        data_inicio = datetime.now() - timedelta(days=dias)
        resultado = db.query(
            Bebida.id,
            Bebida.nome,
            func.sum(ItemPedido.quantidade).label('total_vendido'),
            func.sum(ItemPedido.subtotal).label('receita_gerada')
        ).join(
            ItemPedido, Bebida.id == ItemPedido.bebida_id
        ).join(
            Pedido, ItemPedido.pedido_id == Pedido.id
        ).filter(
            Pedido.created_at >= data_inicio,
            Pedido.status != StatusPedidoEnum.CANCELADO
        ).group_by(
            Bebida.id, Bebida.nome
        ).order_by(
            desc('total_vendido')
        ).limit(limite).all()
        return [
            {
                "bebida_id": r.id,
                "nome_bebida": r.nome,
                "total_vendido": r.total_vendido or 0,
                "receita_gerada": float(r.receita_gerada or 0)
            } for r in resultado
        ]

    def relatorio_periodo_dict(self, data_inicio: datetime, data_fim: datetime) -> dict:
        """Retorna relatório detalhado de um período como dict serializável"""
        from sqlalchemy import func, desc
        from database.models import Pedido, Bebida, ItemPedido, StatusPedidoEnum
        db = self.db
        pedidos = db.query(Pedido).filter(
            Pedido.created_at >= data_inicio,
            Pedido.created_at <= data_fim,
            Pedido.status != StatusPedidoEnum.CANCELADO
        ).all()
        total_pedidos = len(pedidos)
        receita_total = sum(p.total_final for p in pedidos)
        ticket_medio = receita_total / total_pedidos if total_pedidos > 0 else 0.0
        bebidas_ranking = db.query(
            Bebida.id,
            Bebida.nome,
            func.sum(ItemPedido.quantidade).label('total_vendido'),
            func.sum(ItemPedido.subtotal).label('receita_gerada')
        ).join(
            ItemPedido, Bebida.id == ItemPedido.bebida_id
        ).join(
            Pedido, ItemPedido.pedido_id == Pedido.id
        ).filter(
            Pedido.created_at >= data_inicio,
            Pedido.created_at <= data_fim,
            Pedido.status != StatusPedidoEnum.CANCELADO
        ).group_by(
            Bebida.id, Bebida.nome
        ).order_by(
            desc('total_vendido')
        ).limit(10).all()
        bebidas_mais_vendidas = [
            {
                "bebida_id": b.id,
                "nome_bebida": b.nome,
                "total_vendido": b.total_vendido or 0,
                "receita_gerada": float(b.receita_gerada or 0)
            } for b in bebidas_ranking
        ]
        return {
            "periodo_inicio": data_inicio,
            "periodo_fim": data_fim,
            "total_pedidos": total_pedidos,
            "receita_total": receita_total,
            "ticket_medio": ticket_medio,
            "bebidas_mais_vendidas": bebidas_mais_vendidas
        }

    def pedidos_tempo_real_dict(self) -> dict:
        """Retorna pedidos em tempo real para a cozinha como dict serializável"""
        from database.models import StatusPedidoEnum
        pedidos_cozinha = self.obter_pedidos_cozinha()
        now = datetime.now()
        return {
            "pedidos_pendentes": [
                {
                    "id": p.id,
                    "cliente_nome": p.cliente.nome,
                    "total_final": float(p.total_final),
                    "created_at": p.created_at,
                    "tempo_espera_minutos": int((now - p.created_at).total_seconds() / 60),
                    "itens": [
                        {
                            "bebida": item.bebida.nome,
                            "quantidade": item.quantidade
                        } for item in p.itens
                    ]
                } for p in pedidos_cozinha if p.status == StatusPedidoEnum.PENDENTE
            ],
            "pedidos_em_preparo": [
                {
                    "id": p.id,
                    "cliente_nome": p.cliente.nome,
                    "total_final": float(p.total_final),
                    "created_at": p.created_at,
                    "tempo_preparo_minutos": int((now - p.updated_at).total_seconds() / 60),
                    "itens": [
                        {
                            "bebida": item.bebida.nome,
                            "quantidade": item.quantidade
                        } for item in p.itens
                    ]
                } for p in pedidos_cozinha if p.status == StatusPedidoEnum.EM_PREPARO
            ]
        }

    def grafico_vendas_dict(self, dias: int) -> dict:
        """Retorna dados para gráfico de vendas como dict serializável"""
        from sqlalchemy import func
        from database.models import Pedido, StatusPedidoEnum
        db = self.db
        data_inicio = datetime.now() - timedelta(days=dias)
        vendas_por_dia = db.query(
            func.date(Pedido.created_at).label('data'),
            func.count(Pedido.id).label('total_pedidos'),
            func.sum(Pedido.total_final).label('receita_dia')
        ).filter(
            Pedido.created_at >= data_inicio,
            Pedido.status != StatusPedidoEnum.CANCELADO
        ).group_by(
            func.date(Pedido.created_at)
        ).order_by('data').all()
        return {
            "periodo_dias": dias,
            "vendas_por_dia": [
                {
                    "data": v.data.isoformat(),
                    "total_pedidos": v.total_pedidos,
                    "receita_dia": float(v.receita_dia or 0)
                } for v in vendas_por_dia
            ]
        }

    def resumo_cliente_dict(self, cliente_id: int) -> dict:
        """Retorna resumo do cliente logado como dict serializável"""
        from sqlalchemy import func, desc
        from database.models import Pedido, StatusPedidoEnum
        db = self.db
        pedidos = db.query(Pedido).filter(
            Pedido.cliente_id == cliente_id
        ).order_by(desc(Pedido.created_at)).limit(5).all()
        total_gasto = db.query(func.sum(Pedido.total_final)).filter(
            Pedido.cliente_id == cliente_id,
            Pedido.status != StatusPedidoEnum.CANCELADO
        ).scalar() or 0
        total_pedidos = db.query(func.count(Pedido.id)).filter(
            Pedido.cliente_id == cliente_id
        ).scalar() or 0
        cliente = self.cliente_repo.get_by_id(cliente_id)
        return {
            "cliente_nome": getattr(cliente, "nome", None),
            "pontos_fidelidade": getattr(cliente, "pontos_fidelidade", 0),
            "total_pedidos": total_pedidos,
            "total_gasto": float(total_gasto),
            "pedidos_recentes": [
                {
                    "id": p.id,
                    "status": p.status.value,
                    "total_final": float(p.total_final),
                    "created_at": p.created_at
                } for p in pedidos
            ]
        }

    def obter_pedido_detalhado_dict(self, pedido_id: int) -> dict:
        """Retorna um dicionário serializável com todos os campos esperados pelo PedidoDetalhesResponse"""
        from fastapi import HTTPException, status
        try:
            pedido = self.obter_pedido(pedido_id)
            if not pedido:
                return {}
            def is_column(val):
                return hasattr(val, '__class__') and 'sqlalchemy' in str(type(val))
            # Campos principais
            d = {}
            val = getattr(pedido, "id", None)
            d["id"] = int(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) and str(val).isdigit() else None
            val = getattr(pedido, "cliente_id", None)
            d["cliente_id"] = int(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) and str(val).isdigit() else None
            cliente_nome = None
            cliente = getattr(pedido, "cliente", None)
            if cliente is not None and not is_column(cliente):
                nome = getattr(cliente, "nome", None)
                cliente_nome = str(nome) if nome is not None and not is_column(nome) else None
            d["cliente_nome"] = cliente_nome
            status_val = getattr(pedido, "status", None)
            if status_val is not None and not is_column(status_val):
                d["status"] = str(getattr(status_val, "value", status_val))
            else:
                d["status"] = None
            val = getattr(pedido, "total", None)
            d["total"] = float(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) else None
            val = getattr(pedido, "desconto", None)
            d["desconto"] = float(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) else None
            val = getattr(pedido, "total_final", None)
            d["total_final"] = float(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) else None
            metodo_pagamento = getattr(pedido, "metodo_pagamento", None)
            if metodo_pagamento is not None and not is_column(metodo_pagamento):
                d["metodo_pagamento"] = str(getattr(metodo_pagamento, "value", metodo_pagamento))
            else:
                d["metodo_pagamento"] = None
            val = getattr(pedido, "created_at", None)
            d["data_pedido"] = val if val is not None and not is_column(val) else None
            val = getattr(pedido, "updated_at", None)
            d["data_atualizacao"] = val if val is not None and not is_column(val) else None
            obs = getattr(pedido, "observacoes", None)
            d["observacoes"] = str(obs) if obs is not None and not is_column(obs) else None
            itens = getattr(pedido, "itens", None)
            # Corrigir contagem de itens: garantir lista e robustez contra None/Column
            try:
                if itens is not None and not is_column(itens):
                    # Se for iterável, transforma em lista
                    itens_list = list(itens) if not isinstance(itens, list) else itens
                    d["itens_count"] = len(itens_list)
                else:
                    d["itens_count"] = 0
            except Exception:
                d["itens_count"] = 0
            # Itens detalhados
            itens_list = []
            if itens:
                for item in itens:
                    item_dict = {}
                    item_dict["id"] = getattr(item, "id", None)
                    bebida = getattr(item, "bebida", None)
                    item_dict["bebida_nome"] = getattr(bebida, "nome", None) if bebida else None
                    item_dict["bebida_descricao"] = getattr(bebida, "descricao", None) if bebida else None
                    item_dict["quantidade"] = getattr(item, "quantidade", None)
                    item_dict["preco_unitario"] = getattr(item, "preco_unitario", None)
                    item_dict["subtotal"] = getattr(item, "subtotal", None)
                    personalizacoes = getattr(item, "personalizacoes", None)
                    pers_list = []
                    if personalizacoes:
                        for pers in personalizacoes:
                            pers_dict = {}
                            personalizacao = getattr(pers, "personalizacao", None)
                            pers_dict["nome"] = getattr(personalizacao, "nome", None) if personalizacao else None
                            pers_dict["preco_adicional"] = getattr(personalizacao, "preco_adicional", None) if personalizacao else None
                            pers_list.append(pers_dict)
                    item_dict["personalizacoes"] = pers_list
                    itens_list.append(item_dict)
            d["itens"] = itens_list
            # Histórico detalhado
            historico = getattr(pedido, "historico", None)
            hist_list = []
            if historico:
                for hist in historico:
                    hist_dict = {}
                    status_ant = getattr(hist, "status_anterior", None)
                    hist_dict["status_anterior"] = status_ant.value if status_ant and hasattr(status_ant, "value") else None
                    status_novo = getattr(hist, "status_novo", None)
                    hist_dict["status_novo"] = status_novo.value if status_novo and hasattr(status_novo, "value") else None
                    hist_dict["observacao"] = getattr(hist, "observacao", None)
                    hist_dict["timestamp"] = getattr(hist, "timestamp", None)
                    hist_list.append(hist_dict)
            d["historico"] = hist_list
            return d
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao detalhar pedido: {str(e)}"
            )

    def listar_pedidos_dict(self, cliente_id: Optional[int], status_filtro: Optional[str], skip: int, limit: int) -> list:
        """Lista pedidos com filtros, retorna lista de dicts prontos para o Pydantic"""
        # Decide a fonte dos pedidos
        if cliente_id:
            pedidos = self.obter_pedidos_por_cliente(cliente_id)
        elif status_filtro:
            try:
                from database.models import StatusPedidoEnum
                status_enum = StatusPedidoEnum(status_filtro)
                pedidos = self.obter_pedidos_por_status(status_enum)
            except Exception:
                pedidos = []
        else:
            repo = PedidoRepository(self.db)
            pedidos = repo.get_all(skip, limit)
        def is_column(val):
            return hasattr(val, '__class__') and 'sqlalchemy' in str(type(val))
        resultado = []
        for pedido in pedidos:
            d = {}
            val = getattr(pedido, "id", None)
            d["id"] = int(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) and str(val).isdigit() else None
            val = getattr(pedido, "cliente_id", None)
            d["cliente_id"] = int(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) and str(val).isdigit() else None
            status_val = getattr(pedido, "status", None)
            if status_val is not None and not is_column(status_val):
                d["status"] = str(getattr(status_val, "value", status_val))
            else:
                d["status"] = None
            val = getattr(pedido, "total", None)
            d["total"] = float(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) else None
            val = getattr(pedido, "desconto", None)
            d["desconto"] = float(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) else None
            val = getattr(pedido, "total_final", None)
            d["total_final"] = float(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) else None
            metodo_pagamento = getattr(pedido, "metodo_pagamento", None)
            if metodo_pagamento is not None and not is_column(metodo_pagamento):
                d["metodo_pagamento"] = str(getattr(metodo_pagamento, "value", metodo_pagamento))
            else:
                d["metodo_pagamento"] = None
            val = getattr(pedido, "created_at", None)
            d["data_pedido"] = val if val is not None and not is_column(val) else None
            val = getattr(pedido, "updated_at", None)
            d["data_atualizacao"] = val if val is not None and not is_column(val) else None
            obs = getattr(pedido, "observacoes", None)
            d["observacoes"] = str(obs) if obs is not None and not is_column(obs) else None
            cliente_nome = None
            cliente = getattr(pedido, "cliente", None)
            if cliente is not None and not is_column(cliente):
                nome = getattr(cliente, "nome", None)
                cliente_nome = str(nome) if nome is not None and not is_column(nome) else None
            d["cliente_nome"] = cliente_nome
            itens = getattr(pedido, "itens", None)
            # Sempre consulta o banco se a relação vier vazia ou não carregada
            try:
                from database.models import ItemPedido
                if hasattr(self, 'db') and hasattr(pedido, 'id'):
                    count = self.db.query(ItemPedido).filter(ItemPedido.pedido_id == pedido.id).count()
                    d["itens_count"] = count
                else:
                    d["itens_count"] = 0
            except Exception:
                d["itens_count"] = 0
            resultado.append(d)
        return resultado

    def historico_cliente_dict(self, cliente_id: int) -> list:
        """Retorna histórico de pedidos do cliente como lista de dicts prontos para o Pydantic, robusto para Column/None"""
        pedidos = self.obter_pedidos_por_cliente(cliente_id)
        resultado = []
        for pedido in pedidos:
            d = {}
            def is_column(val):
                return hasattr(val, '__class__') and 'sqlalchemy' in str(type(val))
            # id
            val = getattr(pedido, "id", None)
            d["id"] = val if val is not None and not is_column(val) else None
            # cliente_id
            val = getattr(pedido, "cliente_id", None)
            d["cliente_id"] = val if val is not None and not is_column(val) else None
            # status
            status_val = getattr(pedido, "status", None)
            if status_val is not None and not is_column(status_val):
                d["status"] = str(status_val.value) if hasattr(status_val, "value") else str(status_val)
            else:
                d["status"] = None
            # total
            val = getattr(pedido, "total", None)
            d["total"] = val if val is not None and not is_column(val) else None
            # desconto
            val = getattr(pedido, "desconto", None)
            d["desconto"] = val if val is not None and not is_column(val) else None
            # total_final
            val = getattr(pedido, "total_final", None)
            d["total_final"] = val if val is not None and not is_column(val) else None
            # metodo_pagamento
            metodo_pagamento = getattr(pedido, "metodo_pagamento", None)
            if metodo_pagamento is not None and not is_column(metodo_pagamento):
                d["metodo_pagamento"] = str(metodo_pagamento.value) if hasattr(metodo_pagamento, "value") else str(metodo_pagamento)
            else:
                d["metodo_pagamento"] = None
            # datas
            val = getattr(pedido, "created_at", None)
            d["data_pedido"] = val if val is not None and not is_column(val) else None
            val = getattr(pedido, "updated_at", None)
            d["data_atualizacao"] = val if val is not None and not is_column(val) else None
            # observacoes
            obs = getattr(pedido, "observacoes", None)
            d["observacoes"] = str(obs) if obs is not None and not is_column(obs) else None
            # cliente_nome
            cliente_nome = None
            if hasattr(pedido, "cliente") and pedido.cliente:
                nome = getattr(pedido.cliente, "nome", None)
                cliente_nome = str(nome) if nome is not None and not is_column(nome) else None
            d["cliente_nome"] = cliente_nome
            # itens_count
            itens = getattr(pedido, "itens", None)
            if itens is not None:
                try:
                    itens_list = list(itens)
                except Exception:
                    itens_list = []
            else:
                itens_list = []
            d["itens_count"] = len(itens_list)
            resultado.append(d)
        return resultado

    def criar_pedido_completo(self, cliente_id: int, metodo_pagamento_str: str) -> dict:
        """Cria novo pedido usando Command Pattern e retorna dict pronto para o controller"""
        from fastapi import HTTPException, status
        from database.models import MetodoPagamentoEnum
        from patterns.command import CriarPedidoCommand, CommandInvoker
        try:
            try:
                metodo_pagamento = MetodoPagamentoEnum(metodo_pagamento_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Método de pagamento inválido. Use: dinheiro, cartao, pix, fidelidade"
                )

            # Executa comando de criação de pedido
            comando = CriarPedidoCommand(self, cliente_id, metodo_pagamento)
            invoker = CommandInvoker()
            invoker.executar_comando(comando)
            pedido_id = comando.pedido_id if hasattr(comando, 'pedido_id') else None
            if not pedido_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Erro ao criar pedido. Verifique se o carrinho não está vazio."
                )

            pedido = self.obter_pedido(pedido_id)
            # O método processar_pagamento já aplica o desconto correto
            self.processar_pagamento(pedido_id, metodo_pagamento)
            # Buscar novamente para garantir valores atualizados
            pedido = self.obter_pedido(pedido_id)
            # Montar dict para o Pydantic (robusto contra Column/None)
            def is_column(val):
                return hasattr(val, '__class__') and 'sqlalchemy' in str(type(val))
            d = {}
            val = getattr(pedido, "id", None)
            d["id"] = int(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) and str(val).isdigit() else None
            val = getattr(pedido, "cliente_id", None)
            d["cliente_id"] = int(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) and str(val).isdigit() else None
            cliente_nome = None
            cliente = getattr(pedido, "cliente", None)
            if cliente is not None and not is_column(cliente):
                nome = getattr(cliente, "nome", None)
                cliente_nome = str(nome) if nome is not None and not is_column(nome) else None
            d["cliente_nome"] = cliente_nome
            status_val = getattr(pedido, "status", None)
            if status_val is not None and not is_column(status_val):
                d["status"] = str(getattr(status_val, "value", status_val))
            else:
                d["status"] = None
            val = getattr(pedido, "total", None)
            d["total"] = float(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) else None
            val = getattr(pedido, "desconto", None)
            d["desconto"] = float(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) else None
            val = getattr(pedido, "total_final", None)
            d["total_final"] = float(val) if val is not None and not is_column(val) and isinstance(val, (int, float, str)) else None
            metodo_pagamento = getattr(pedido, "metodo_pagamento", None)
            if metodo_pagamento is not None and not is_column(metodo_pagamento):
                d["metodo_pagamento"] = str(getattr(metodo_pagamento, "value", metodo_pagamento))
            else:
                d["metodo_pagamento"] = None
            val = getattr(pedido, "created_at", None)
            d["data_pedido"] = val if val is not None and not is_column(val) else None
            val = getattr(pedido, "updated_at", None)
            d["data_atualizacao"] = val if val is not None and not is_column(val) else None
            obs = getattr(pedido, "observacoes", None)
            d["observacoes"] = str(obs) if obs is not None and not is_column(obs) else None
            itens = getattr(pedido, "itens", None)
            if itens is not None and not is_column(itens) and hasattr(itens, '__len__'):
                d["itens_count"] = len(itens)
            else:
                d["itens_count"] = 0
            return d
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao criar pedido: {str(e)}"
            )

    def cancelar_pedido_state_pattern(self, pedido_id: int) -> dict:
        """Cancela pedido usando Command Pattern para orquestração"""
        from patterns.command import CancelarPedidoCommand, CommandInvoker
        comando = CancelarPedidoCommand(self, pedido_id)
        invoker = CommandInvoker()
        invoker.executar_comando(comando)
        return comando.resultado if hasattr(comando, 'resultado') else {"success": False, "message": "Erro ao cancelar pedido"}

    def avancar_estado_pedido(self, pedido_id: int) -> dict:
        """Avança o estado do pedido usando Command Pattern para orquestração"""
        from patterns.command import AvancarEstadoPedidoCommand, CommandInvoker
        comando = AvancarEstadoPedidoCommand(self, pedido_id)
        invoker = CommandInvoker()
        invoker.executar_comando(comando)
        return comando.resultado if hasattr(comando, 'resultado') else {"success": False, "message": "Erro ao avançar estado"}
    """Business Object para gerenciar pedidos"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cliente_repo = ClienteRepository(db)
        self.bebida_repo = BebidaRepository(db)
        self.personalizacao_repo = PersonalizacaoRepository(db)
        self.carrinho_repo = CarrinhoRepository(db)
        self.pedido_repo = PedidoRepository(db)
        
        self.menu_factory = MenuFactory()
        self.command_invoker = CommandInvoker()
        
        # Observers do sistema
        self.cozinha_observer = CozinhaObserver()
        self.observers_clientes: Dict[int, ClienteObserver] = {}
    
    def criar_pedido(self, cliente_id: int, metodo_pagamento: MetodoPagamentoEnum) -> Optional[int]:
            

            subject = PedidoSubject(pedido.id)
            subject.adicionar_observer(self.cozinha_observer)
            subject.adicionar_observer(self.observers_clientes[cliente_id])
            subject.notificar_observers()
            
            val = getattr(pedido, "id", None)
            if val is not None and hasattr(val, '__class__') and 'sqlalchemy' in str(type(val)):
                return None
            return int(val) if val is not None and str(val).isdigit() else None
            
        except Exception as e:
            print(f"Erro ao criar pedido: {e}")
            return None
    
    def processar_pagamento(self, pedido_id: int, metodo_pagamento: MetodoPagamentoEnum) -> Optional[Dict[str, Any]]:
        """Processa pagamento delegando todo cálculo para as strategies"""
        try:
            pedido = self.pedido_repo.get_by_id(pedido_id)
            if not pedido:
                raise ValueError(f"Pedido #{pedido_id} não encontrado")

            # Seleciona a strategy de desconto
            strategy = StrategySelector.criar_strategy(metodo_pagamento)
            if not strategy:
                raise ValueError("Nenhuma strategy de desconto encontrada para o método de pagamento.")

            # Usa o contexto para aplicar a strategy
            contexto = ContextoPagamento()
            contexto.set_strategy(strategy)
            valor_original = pedido.total
            desconto = strategy.calcular_desconto(valor_original)
            valor_final = valor_original - desconto

            return {
                "pedido_id": pedido_id,
                "valor_original": valor_original,
                "desconto": desconto,
                "valor_final": valor_final,
                "metodo_pagamento": metodo_pagamento.value,
                "descricao_desconto": strategy.get_descricao(),
                "status": "processado"
            }
        except Exception as e:
            print(f"Erro ao processar pagamento: {e}")
            return None
    
    def alterar_status(self, pedido_id: int, novo_status: StatusPedidoEnum) -> bool:
        """Altera status do pedido usando State Pattern"""
        try:
            pedido = self.pedido_repo.get_by_id(pedido_id)
            if not pedido:
                return False
            
            # Usar State Pattern para gerenciar transições
            contexto = ContextoPedido()
            contexto.set_pedido_id(pedido_id)
            contexto.set_status(pedido.status)
            
            # Tentar transição
            if contexto.pode_transicionar_para(novo_status):
                # Atualizar no banco
                self.pedido_repo.update_status(pedido_id, novo_status)
                
                # Notificar observers
                if pedido.cliente_id in self.observers_clientes:
                    subject = PedidoSubject(pedido_id)
                    subject.adicionar_observer(self.observers_clientes[pedido.cliente_id])
                    subject.notificar_observers()
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Erro ao alterar status: {e}")
            return False
    
    def obter_pedido(self, pedido_id: int) -> Optional[Pedido]:
        """Obtém pedido por ID"""
        return self.pedido_repo.get_by_id(pedido_id)
    
    def obter_pedidos_por_cliente(self, cliente_id: int) -> List[Pedido]:
        """Obtém histórico de pedidos do cliente"""
        return self.pedido_repo.get_by_cliente(cliente_id)
    
    def obter_pedidos_por_status(self, status: StatusPedidoEnum) -> List[Pedido]:
        """Obtém pedidos por status"""
        return self.pedido_repo.get_by_status(status)
    
    def obter_pedidos_cozinha(self) -> List[Pedido]:
        """Obtém pedidos para a cozinha"""
        return self.pedido_repo.get_pedidos_cozinha()
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """Obtém estatísticas do sistema"""
        return self.pedido_repo.get_estatisticas()


class ClienteBO:
    def autenticar_cliente_dict(self, identifier: str, password: str) -> Optional[dict]:
        """Autentica cliente por email ou nome e retorna dict serializável ou None"""
        # Primeiro tenta por email
        cliente = self.cliente_repo.get_by_email(identifier)
        # Se não encontrou, tenta por nome
        if not cliente:
            cliente = self.db.query(Cliente).filter(Cliente.nome == identifier).first()
        # Verifica senha
        from src.auth import verify_password
        if cliente and verify_password(password, cliente.senha_hash):
            return self.cliente_response_dict(cliente)
        return None

    def registrar_cliente_dict(self, nome: str, email: str, senha: str) -> dict:
        """Registra novo cliente e retorna dict serializável ou erro"""
        # Verificar se email já existe
        if self.cliente_repo.get_by_email(email):
            return {"error": "Email já cadastrado"}
        # Verificar se nome já existe
        existing_user = self.db.query(Cliente).filter(Cliente.nome == nome).first()
        if existing_user:
            return {"error": "Nome já cadastrado"}
        from src.auth import get_password_hash
        hashed_password = get_password_hash(senha)
        cliente = self.cliente_repo.create_cliente(nome, email, hashed_password)
        return self.cliente_response_dict(cliente)

    def cliente_response_dict(self, cliente) -> dict:
        """Retorna dict serializável para UserResponse"""
        return {
            "id": getattr(cliente, "id", None),
            "nome": getattr(cliente, "nome", None),
            "email": getattr(cliente, "email", None),
            "pontos_fidelidade": getattr(cliente, "pontos_fidelidade", 0)
        }
    def atualizar_item_carrinho_dict(self, item_id: int, cliente_id: int, quantidade: int, personalizacoes: Optional[list] = None) -> dict:
        """Atualiza item do carrinho (quantidade e personalizações) e retorna dict serializável para o controller"""
        carrinho_repo = self.carrinho_repo
        item = carrinho_repo.get_by_id(item_id)
        if not item or item.cliente_id != cliente_id or quantidade <= 0:
            return {}
        # Atualiza quantidade e personalizações
        item_atualizado = carrinho_repo.update_item(item_id, quantidade, personalizacoes)
        return {
            "message": "Item atualizado",
            "item_id": item_atualizado.id,
            "nova_quantidade": item_atualizado.quantidade,
            "personalizacoes": [
                {
                    "id": pers.personalizacao.id,
                    "nome": pers.personalizacao.nome,
                    "preco_adicional": pers.personalizacao.preco_adicional
                } for pers in getattr(item_atualizado, "personalizacoes", [])
            ]
        }

    def remover_item_carrinho_dict(self, item_id: int, cliente_id: int) -> dict:
        """Remove item do carrinho e retorna dict serializável para o controller"""
        carrinho_repo = self.carrinho_repo
        item = carrinho_repo.get_by_id(item_id)
        if not item or item.cliente_id != cliente_id:
            return {}
        carrinho_repo.delete(item_id)
        return {"message": "Item removido do carrinho"}

    def limpar_carrinho_dict(self, cliente_id: int) -> dict:
        """Limpa carrinho do cliente e retorna dict serializável para o controller"""
        if self.limpar_carrinho(cliente_id):
            return {"message": "Carrinho limpo com sucesso"}
        else:
            return {}
    def obter_carrinho_dict(self, cliente_id: int) -> dict:
        """Retorna o carrinho do cliente como dict serializável para o controller, sem personalizações duplicadas ou inesperadas"""
        itens_carrinho = self.obter_carrinho(cliente_id)
        itens_response = []
        total_valor = 0.0
        for item in itens_carrinho:
            subtotal = item.preco_unitario * item.quantidade
            total_valor += subtotal
            # Deduplicar personalizações por nome, priorizando a última ocorrência (mais recente)
            personalizacoes_dict = {}
            for pers in getattr(item, "personalizacoes", []):
                personalizacao_obj = pers.personalizacao if hasattr(pers, "personalizacao") else pers
                pers_nome = getattr(personalizacao_obj, "nome", None)
                if pers_nome:
                    # Sempre sobrescreve, assim a última ocorrência para o nome fica registrada
                    personalizacoes_dict[pers_nome] = {
                        "id": getattr(personalizacao_obj, "id", None),
                        "nome": pers_nome,
                        "preco_adicional": getattr(personalizacao_obj, "preco_adicional", None)
                    }
            personalizacoes = list(personalizacoes_dict.values())
            itens_response.append({
                "id": item.id,
                "bebida_id": item.bebida.id,
                "bebida_nome": item.bebida.nome,
                "bebida_descricao": item.bebida.descricao,
                "quantidade": item.quantidade,
                "preco_unitario": item.preco_unitario,
                "subtotal": subtotal,
                "personalizacoes": personalizacoes,
                "observacoes": item.observacoes
            })
        return {
            "itens": itens_response,
            "total_itens": len(itens_carrinho),
            "total_valor": total_valor
        }

    def adicionar_ao_carrinho_dict(self, cliente_id: int, bebida_id: int, quantidade: int = 1, personalizacoes: Optional[list] = None, observacoes: Optional[str] = None) -> dict:
        """Adiciona item ao carrinho e retorna dict serializável para o controller"""
        item = self.adicionar_ao_carrinho(cliente_id, bebida_id, quantidade, personalizacoes, observacoes)
        if not item:
            return {"error": "Não foi possível adicionar o item ao carrinho"}
        return {
            "message": "Item adicionado ao carrinho",
            "item_id": item.id
        }
    """Business Object para gerenciar clientes"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cliente_repo = ClienteRepository(db)
        self.bebida_repo = BebidaRepository(db)
        self.personalizacao_repo = PersonalizacaoRepository(db)
        self.carrinho_repo = CarrinhoRepository(db)
        self.menu_factory = MenuFactory()
    
    def cadastrar_cliente(self, nome: str, email: str, password: str) -> Optional[Cliente]:
        """Cadastra novo cliente"""
        try:
            # Verificar se email já existe
            if self.cliente_repo.get_by_email(email):
                raise ValueError("Email já cadastrado")
            
            cliente = self.cliente_repo.create_cliente(nome, email, password)
            return cliente
            
        except Exception as e:
            print(f"Erro ao cadastrar cliente: {e}")
            return None
    
    def autenticar_cliente(self, email: str, password: str) -> Optional[Cliente]:
        """Autentica cliente"""
        return self.cliente_repo.authenticate(email, password)
    
    def obter_cliente(self, cliente_id: int) -> Optional[Cliente]:
        """Obtém cliente por ID"""
        return self.cliente_repo.get_by_id(cliente_id)
    
    def buscar_por_email(self, email: str) -> Optional[Cliente]:
        """Busca cliente por email"""
        return self.cliente_repo.get_by_email(email)
    
    def adicionar_ao_carrinho(self, cliente_id: int, bebida_id: int, quantidade: int = 1, 
                            personalizacoes: Optional[List[int]] = None, observacoes: Optional[str] = None) -> Optional[ItemCarrinho]:
        """Adiciona item ao carrinho agrupando itens idênticos (mesma bebida, mesmo conjunto de nomes de personalização, mesmas observações)"""
        try:
            bebida = self.bebida_repo.get_by_id(bebida_id)
            if not bebida:
                raise ValueError("Bebida não encontrada")
            tipo_bebida = getattr(bebida, "tipo", None)
            tipo_bebida_str = tipo_bebida.value if tipo_bebida is not None else None
            factory = BebidaFactorySelector.obter_factory(tipo_bebida_str or "")
            if not factory:
                raise ValueError("Tipo de bebida inválido")
            from patterns.decorator import aplicar_personalizacoes
            # Garante personalizacoes sem duplicatas
            personalizacoes = list(dict.fromkeys(personalizacoes)) if personalizacoes else []
            # Buscar nomes das personalizações novas
            nomes_pers_novas = set()
            for pid in personalizacoes:
                pers_obj = self.personalizacao_repo.get_by_id(pid) if hasattr(self.personalizacao_repo, 'get_by_id') else self.personalizacao_repo.obter_por_id(pid)
                if pers_obj:
                    nome = getattr(pers_obj, "nome", None)
                    if nome:
                        nomes_pers_novas.add(str(nome))
            obs_nova = (observacoes or "").strip() if observacoes else ""
            itens_carrinho = self.carrinho_repo.get_by_cliente(cliente_id)
            for item in itens_carrinho:
                bebida_id_item = getattr(item, "bebida_id", None)
                if bebida_id_item is not None and int(bebida_id_item) == int(bebida_id):
                    # Buscar nomes das personalizações existentes
                    nomes_pers_existentes = set()
                    for p in getattr(item, "personalizacoes", []):
                        pers_obj = getattr(p, "personalizacao", None) if hasattr(p, "personalizacao") else p
                        nome = getattr(pers_obj, "nome", None)
                        if nome:
                            nomes_pers_existentes.add(str(nome))
                    obs_existente = getattr(item, "observacoes", None)
                    obs_existente = str(obs_existente).strip() if obs_existente is not None else ""
                    # Se nomes e observações forem iguais, agrupa
                    if nomes_pers_existentes == nomes_pers_novas and obs_existente == obs_nova:
                        quantidade_atual = getattr(item, "quantidade", 0)
                        try:
                            quantidade_atual = int(quantidade_atual)
                        except Exception:
                            quantidade_atual = 0
                        nova_quantidade = quantidade_atual + int(quantidade)
                        setattr(item, "quantidade", nova_quantidade)
                        self.carrinho_repo.db.commit()
                        self.carrinho_repo.db.refresh(item)
                        return item
            # Se não existe igual, adiciona novo item normalmente
            componente_base = factory.criar_bebida()
            if personalizacoes:
                _ = aplicar_personalizacoes(componente_base, personalizacoes, self.personalizacao_repo)
            return self.carrinho_repo.add_item(cliente_id, bebida_id, quantidade, personalizacoes, observacoes)
        except Exception as e:
            print(f"Erro ao adicionar ao carrinho: {e}")
            return None
    
    def obter_carrinho(self, cliente_id: int) -> List[ItemCarrinho]:
        """Obtém itens do carrinho do cliente"""
        return self.carrinho_repo.get_by_cliente(cliente_id)
    
    def limpar_carrinho(self, cliente_id: int) -> bool:
        """Limpa carrinho do cliente"""
        try:
            self.carrinho_repo.clear_carrinho(cliente_id)
            return True
        except Exception as e:
            print(f"Erro ao limpar carrinho: {e}")
            return False
    
    def obter_total_carrinho(self, cliente_id: int) -> float:
        """Obtém total do carrinho"""
        return self.carrinho_repo.get_total_carrinho(cliente_id)


class ProdutoBO:
    def listar_personalizacoes_dict(self, categoria: Optional[str] = None) -> list:
        """Lista personalizações disponíveis, opcionalmente filtradas por categoria, como dicts serializáveis"""
        try:
            if categoria:
                personalizacoes = self.personalizacao_repo.get_by_categoria(categoria)
            else:
                personalizacoes = self.personalizacao_repo.get_all()
            # Filtrar apenas disponíveis e garantir tipos serializáveis
            def is_disponivel(p):
                val = getattr(p, 'disponivel', True)
                return bool(val) if not hasattr(val, 'clauses') else True
            personalizacoes_disponiveis = [p for p in personalizacoes if is_disponivel(p)]
            return [
                {
                    "id": int(getattr(pers, "id", 0)),
                    "nome": str(getattr(pers, "nome", "")),
                    "preco_adicional": float(getattr(pers, "preco_adicional", 0.0)),
                    "categoria": str(getattr(pers, "categoria", "geral")) or "geral",
                    "disponivel": bool(getattr(pers, "disponivel", True))
                }
                for pers in personalizacoes_disponiveis
            ]
        except Exception as e:
            raise Exception(f"Erro ao listar personalizações: {str(e)}")

    def listar_personalizacoes_bebida_dict(self, bebida_id: int) -> list:
        """Lista personalizações disponíveis para uma bebida específica como dicts serializáveis"""
        try:
            personalizacoes = self.personalizacao_repo.get_by_bebida(bebida_id)
            def is_disponivel(p):
                val = getattr(p, 'disponivel', True)
                return bool(val) if not hasattr(val, 'clauses') else True
            personalizacoes_disponiveis = [p for p in personalizacoes if is_disponivel(p)]
            return [
                {
                    "id": int(getattr(pers, "id", 0)),
                    "nome": str(getattr(pers, "nome", "")),
                    "preco_adicional": float(getattr(pers, "preco_adicional", 0.0)),
                    "categoria": str(getattr(pers, "categoria", "geral")) or "geral",
                    "disponivel": bool(getattr(pers, "disponivel", True))
                }
                for pers in personalizacoes_disponiveis
            ]
        except Exception as e:
            raise Exception(f"Erro ao listar personalizações da bebida: {str(e)}")

    def listar_categorias_personalizacao_dict(self) -> dict:
        """Obtém categorias de personalizações disponíveis como dict serializável"""
        try:
            todas_personalizacoes = self.personalizacao_repo.get_all()
            categorias = {}
            for pers in todas_personalizacoes:
                if bool(getattr(pers, 'disponivel', True)):
                    categoria = str(getattr(pers, 'categoria', 'geral')) or 'geral'
                    if categoria not in categorias:
                        categorias[categoria] = []
                    categorias[categoria].append(str(getattr(pers, 'nome', '')))
            return categorias
        except Exception as e:
            raise Exception(f"Erro ao obter categorias: {str(e)}")
    def criar_bebida_dict(self, nome: str, preco_base: float, tipo: TipoBebidasEnum, descricao: Optional[str] = None, disponivel: bool = True) -> dict:
        """Cria uma nova bebida e retorna dict serializável para o controller"""
        # Verifica se já existe bebida com o mesmo nome
        bebida_existente = self.bebida_repo.obter_por_nome(nome)
        if bebida_existente:
            return {}
        bebida = self.criar_bebida(nome, preco_base, tipo, descricao, disponivel)
        bebida_id = getattr(bebida, 'id', None)
        if bebida_id is not None and hasattr(bebida_id, '__int__') and bebida_id is not None:
            bebida_id_int = int(bebida_id)
            return self.obter_bebida_dict(bebida_id_int)
        return {}

    def atualizar_bebida_dict(self, bebida_id: int, dados_atualizacao: Dict[str, Any]) -> dict:
        """Atualiza uma bebida e retorna dict serializável para o controller"""
        bebida = self.atualizar_bebida(bebida_id, dados_atualizacao)
        if not bebida:
            return {}
        bebida_id_val = getattr(bebida, 'id', None)
        if bebida_id_val is not None and hasattr(bebida_id_val, '__int__'):
            bebida_id_int = int(bebida_id_val)
            return self.obter_bebida_dict(bebida_id_int)
        return {}
    def personalizar_bebida_dict(self, bebida_id: int, personalizacoes_ids: list) -> dict:
        """Orquestra a personalização de bebida usando Factory e Decorator"""
        try:
            bebida = self.bebida_repo.obter_por_id(bebida_id)
            if not bebida:
                return {}
            tipo_bebida = getattr(bebida, "tipo", None)
            tipo_bebida_str = tipo_bebida.value if tipo_bebida is not None else None
            factory = BebidaFactorySelector.obter_factory(tipo_bebida_str or "")
            if not factory:
                return {}
            bebida_componente = factory.criar_bebida()
            from patterns.decorator import aplicar_personalizacoes
            bebida_final = aplicar_personalizacoes(bebida_componente, personalizacoes_ids, self.personalizacao_repo)
            # Monta lista de nomes das personalizações aplicadas
            personalizacoes_aplicadas = [
                getattr(self.personalizacao_repo.obter_por_id(p_id), "nome", "")
                for p_id in personalizacoes_ids
                if self.personalizacao_repo.obter_por_id(p_id) is not None and getattr(self.personalizacao_repo.obter_por_id(p_id), 'disponivel', True)
            ]
            return {
                "descricao": bebida_final.get_descricao(),
                "preco_final": bebida_final.get_preco(),
                "tipo": bebida_final.get_tipo(),
                "personalizacoes_aplicadas": personalizacoes_aplicadas
            }
        except Exception as e:
            return {"erro": f"Erro ao personalizar bebida: {str(e)}"}

    def obter_bebida_dict(self, bebida_id: int) -> dict:
        """Retorna um dicionário serializável para BebidaResponse"""
        try:
            bebida = self.bebida_repo.obter_por_id(bebida_id)
            if not bebida:
                return {}
            tipo_bebida = getattr(bebida, "tipo", None)
            d = {
                "id": getattr(bebida, "id", None),
                "nome": getattr(bebida, "nome", None),
                "preco_base": getattr(bebida, "preco_base", None),
                "tipo": tipo_bebida.value if tipo_bebida is not None else None,
                "descricao": getattr(bebida, "descricao", None),
                "disponivel": getattr(bebida, "disponivel", None),
                "personalizacoes_disponiveis": []
            }
            bebida_id = getattr(bebida, "id", None)
            if isinstance(bebida_id, int):
                personalizacoes = self.personalizacao_repo.obter_por_bebida(bebida_id)
            else:
                personalizacoes = []
            d["personalizacoes_disponiveis"] = [
                {
                    "id": getattr(p, "id", None),
                    "nome": getattr(p, "nome", None),
                    "preco_adicional": getattr(p, "preco_adicional", None),
                    "categoria": getattr(p, "categoria", None)
                } for p in personalizacoes
            ]
            return d
        except Exception as e:
            raise Exception(f"Erro ao detalhar bebida: {str(e)}")

    def obter_menu_completo_dict(self) -> dict:
        """Retorna um dicionário serializável para MenuResponse"""
        try:
            tipos_disponiveis = self.menu_factory.get_tipos_disponiveis()
            bebidas_dict = self.listar_bebidas_dict(disponivel=True)
            return {
                "bebidas_disponiveis": bebidas_dict,
                "tipos_bebidas": tipos_disponiveis,
                "total_bebidas": len(bebidas_dict)
            }
        except Exception as e:
            raise Exception(f"Erro ao montar menu: {str(e)}")

    def listar_bebidas_dict(self, tipo: Optional[str] = None, disponivel: Optional[bool] = True) -> list:
        """Retorna lista de bebidas como dicionários serializáveis para o controller"""
        try:
            bebidas = self.bebida_repo.listar_bebidas(tipo=tipo, disponivel=disponivel)
            resultado = []
            for bebida in bebidas:
                tipo_bebida = getattr(bebida, "tipo", None)
                d = {
                    "id": getattr(bebida, "id", None),
                    "nome": getattr(bebida, "nome", None),
                    "preco_base": getattr(bebida, "preco_base", None),
                    "tipo": tipo_bebida.value if tipo_bebida is not None else None,
                    "descricao": getattr(bebida, "descricao", None),
                    "disponivel": getattr(bebida, "disponivel", None),
                    "personalizacoes_disponiveis": []
                }
                bebida_id = getattr(bebida, "id", None)
                if isinstance(bebida_id, int):
                    personalizacoes = self.personalizacao_repo.obter_por_bebida(bebida_id)
                else:
                    personalizacoes = []
                d["personalizacoes_disponiveis"] = [
                    {
                        "id": getattr(p, "id", None),
                        "nome": getattr(p, "nome", None),
                        "preco_adicional": getattr(p, "preco_adicional", None),
                        "categoria": getattr(p, "categoria", None)
                    } for p in personalizacoes
                ]
                resultado.append(d)
            return resultado
        except Exception as e:
            raise Exception(f"Erro ao listar bebidas: {str(e)}")
    """Business Object para gerenciar produtos/bebidas"""
    
    def __init__(self, db: Session):
        self.db = db
        self.bebida_repo = BebidaRepository(db)
        self.personalizacao_repo = PersonalizacaoRepository(db)
        self.menu_factory = MenuFactory()
    
    def listar_bebidas(self) -> List[Bebida]:
        """Lista todas as bebidas disponíveis"""
        return self.bebida_repo.get_disponiveis()
    
    def listar_bebidas_por_tipo(self, tipo: TipoBebidasEnum) -> List[Bebida]:
        """Lista bebidas por tipo"""
        return self.bebida_repo.get_by_tipo(tipo)
    
    def buscar_bebidas(self, query: str) -> List[Bebida]:
        """Busca bebidas por nome/descrição"""
        return self.bebida_repo.search(query)
    
    def obter_bebida(self, bebida_id: int) -> Optional[Bebida]:
        """Obtém bebida por ID"""
        return self.bebida_repo.get_by_id(bebida_id)
    
    def obter_personalizacoes(self, bebida_id: int) -> List:
        """Obtém personalizações disponíveis para uma bebida"""
        return self.personalizacao_repo.get_by_bebida(bebida_id)
    
    def criar_bebida(self, nome: str, preco_base: float, tipo: TipoBebidasEnum, 
                    descricao: Optional[str] = None, disponivel: bool = True) -> Bebida:
        """Cria uma nova bebida"""
        bebida = Bebida(
            nome=nome,
            preco_base=preco_base,
            tipo=tipo,
            descricao=descricao,
            disponivel=disponivel
        )
        return self.bebida_repo.create(bebida)
    
    def atualizar_bebida(self, bebida_id: int, dados_atualizacao: Dict[str, Any]) -> Optional[Bebida]:
        """Atualiza uma bebida existente"""
        # Converter string de tipo para enum se necessário
        if 'tipo' in dados_atualizacao and isinstance(dados_atualizacao['tipo'], str):
            dados_atualizacao['tipo'] = TipoBebidasEnum(dados_atualizacao['tipo'])
        bebida = self.bebida_repo.update(bebida_id, **dados_atualizacao)
        if bebida is None:
            return None
        return bebida
    
    def deletar_bebida(self, bebida_id: int) -> bool:
        """Deleta uma bebida"""
        return self.bebida_repo.delete(bebida_id) is not None
    
    def bebida_tem_pedidos(self, bebida_id: int) -> bool:
        """Verifica se a bebida tem pedidos associados"""
        return self.bebida_repo.tem_pedidos_associados(bebida_id)
    
    def criar_bebida_personalizada(self, tipo_bebida: str, nome_bebida: str, personalizacoes_ids: List[int]) -> Optional[ComponenteBebida]:
        """Orquestra a criação de bebida personalizada usando Factory e Decorator"""
        try:
            factory = BebidaFactorySelector.obter_factory(tipo_bebida)
            if not factory:
                return None
            bebida_base = factory.criar_bebida()
            from patterns.decorator import aplicar_personalizacoes
            bebida_final = aplicar_personalizacoes(bebida_base, personalizacoes_ids, self.personalizacao_repo)
            return bebida_final
        except Exception as e:
            print(f"Erro ao criar bebida personalizada: {e}")
            return None
            
