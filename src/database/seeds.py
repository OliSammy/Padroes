"""
Sistema de Seeds para popular o banco de dados
"""
from sqlalchemy.orm import Session
from database.config import get_db, init_db
from database.models import *
import bcrypt

def hash_password(password: str) -> str:
    """Hash de senha com bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_bebidas(db: Session):
    """Cria bebidas no banco"""
    # Verificar se já existem bebidas
    bebidas_existentes = db.query(Bebida).count()
    if bebidas_existentes > 0:
        print("⚠️ Bebidas já existem no banco, pulando criação...")
        return db.query(Bebida).all()
    
    bebidas = [
        # Cafés
        Bebida(nome="Espresso", preco_base=3.50, tipo=TipoBebidasEnum.CAFE, 
               descricao="Café espresso tradicional"),
        Bebida(nome="Americano", preco_base=4.00, tipo=TipoBebidasEnum.CAFE,
               descricao="Café americano suave"),
        Bebida(nome="Cappuccino", preco_base=5.50, tipo=TipoBebidasEnum.CAFE,
               descricao="Cappuccino cremoso"),
        Bebida(nome="Latte", preco_base=6.00, tipo=TipoBebidasEnum.CAFE,
               descricao="Café latte com leite vaporizado"),
        Bebida(nome="Mocha", preco_base=6.50, tipo=TipoBebidasEnum.CAFE,
               descricao="Café mocha com chocolate"),
        
        # Chás
        Bebida(nome="Chá Verde", preco_base=3.00, tipo=TipoBebidasEnum.CHA,
               descricao="Chá verde antioxidante"),
        Bebida(nome="Chá Preto", preco_base=3.00, tipo=TipoBebidasEnum.CHA,
               descricao="Chá preto tradicional"),
        Bebida(nome="Chá de Camomila", preco_base=3.50, tipo=TipoBebidasEnum.CHA,
               descricao="Chá de camomila relaxante"),
        Bebida(nome="Earl Grey", preco_base=4.00, tipo=TipoBebidasEnum.CHA,
               descricao="Chá Earl Grey com bergamota"),
        
        # Sucos
        Bebida(nome="Suco de Laranja", preco_base=4.50, tipo=TipoBebidasEnum.SUCO,
               descricao="Suco de laranja natural"),
        Bebida(nome="Suco de Maçã", preco_base=4.50, tipo=TipoBebidasEnum.SUCO,
               descricao="Suco de maçã natural"),
        Bebida(nome="Suco Verde", preco_base=5.00, tipo=TipoBebidasEnum.SUCO,
               descricao="Suco verde detox"),
    ]
    
    for bebida in bebidas:
        db.add(bebida)
    db.commit()
    return bebidas

def create_personalizacoes(db: Session, bebidas: list):
    """Cria personalizações para as bebidas"""
    # Verificar se já existem personalizações
    personalizacoes_existentes = db.query(Personalizacao).count()
    if personalizacoes_existentes > 0:
        print("⚠️ Personalizações já existem no banco, pulando criação...")
        return
    personalizacoes = [
        # Leites alternativos
        Personalizacao(nome="Leite de Aveia", preco_adicional=1.00, categoria="leite"),
        Personalizacao(nome="Leite de Amêndoa", preco_adicional=1.20, categoria="leite"),
        Personalizacao(nome="Leite de Soja", preco_adicional=0.80, categoria="leite"),
        Personalizacao(nome="Leite Desnatado", preco_adicional=0.50, categoria="leite"),
        
        # Adoçantes
        Personalizacao(nome="Sem Açúcar", preco_adicional=0.00, categoria="adocante"),
        Personalizacao(nome="Açúcar Mascavo", preco_adicional=0.30, categoria="adocante"),
        Personalizacao(nome="Stevia", preco_adicional=0.50, categoria="adocante"),
        Personalizacao(nome="Xilitol", preco_adicional=0.70, categoria="adocante"),
        
        # Extras
        Personalizacao(nome="Canela", preco_adicional=0.50, categoria="extra"),
        Personalizacao(nome="Chocolate Extra", preco_adicional=1.00, categoria="extra"),
        Personalizacao(nome="Chantilly", preco_adicional=1.50, categoria="extra"),
        Personalizacao(nome="Caramelo", preco_adicional=1.00, categoria="extra"),
        Personalizacao(nome="Baunilha", preco_adicional=0.80, categoria="extra"),
        
        # Tamanhos
        Personalizacao(nome="Tamanho Grande", preco_adicional=2.00, categoria="tamanho"),
        Personalizacao(nome="Dose Extra", preco_adicional=1.50, categoria="extra"),
    ]
    
    # Associa personalizações às bebidas apropriadas
    for personalizacao in personalizacoes:
        # Leites só para cafés
        if personalizacao.categoria == "leite":
            for bebida in bebidas:
                if bebida.tipo == TipoBebidasEnum.CAFE:
                    nova_pers = Personalizacao(
                        nome=personalizacao.nome,
                        preco_adicional=personalizacao.preco_adicional,
                        categoria=personalizacao.categoria,
                        bebida_id=bebida.id
                    )
                    db.add(nova_pers)
        
        # Adoçantes para todas as bebidas
        elif personalizacao.categoria == "adocante":
            for bebida in bebidas:
                nova_pers = Personalizacao(
                    nome=personalizacao.nome,
                    preco_adicional=personalizacao.preco_adicional,
                    categoria=personalizacao.categoria,
                    bebida_id=bebida.id
                )
                db.add(nova_pers)
        
        # Extras específicos
        elif personalizacao.categoria == "extra":
            for bebida in bebidas:
                # Canela para cafés e chás
                if personalizacao.nome == "Canela" and bebida.tipo in [TipoBebidasEnum.CAFE, TipoBebidasEnum.CHA]:
                    nova_pers = Personalizacao(
                        nome=personalizacao.nome,
                        preco_adicional=personalizacao.preco_adicional,
                        categoria=personalizacao.categoria,
                        bebida_id=bebida.id
                    )
                    db.add(nova_pers)
                
                # Chocolate extra só para cafés
                elif personalizacao.nome == "Chocolate Extra" and bebida.tipo == TipoBebidasEnum.CAFE:
                    nova_pers = Personalizacao(
                        nome=personalizacao.nome,
                        preco_adicional=personalizacao.preco_adicional,
                        categoria=personalizacao.categoria,
                        bebida_id=bebida.id
                    )
                    db.add(nova_pers)
                
                # Chantilly para cafés
                elif personalizacao.nome == "Chantilly" and bebida.tipo == TipoBebidasEnum.CAFE:
                    nova_pers = Personalizacao(
                        nome=personalizacao.nome,
                        preco_adicional=personalizacao.preco_adicional,
                        categoria=personalizacao.categoria,
                        bebida_id=bebida.id
                    )
                    db.add(nova_pers)
                
                # Outros extras para cafés
                elif personalizacao.nome in ["Caramelo", "Baunilha", "Dose Extra"] and bebida.tipo == TipoBebidasEnum.CAFE:
                    nova_pers = Personalizacao(
                        nome=personalizacao.nome,
                        preco_adicional=personalizacao.preco_adicional,
                        categoria=personalizacao.categoria,
                        bebida_id=bebida.id
                    )
                    db.add(nova_pers)
        
        # Tamanho grande para todas
        elif personalizacao.categoria == "tamanho":
            for bebida in bebidas:
                nova_pers = Personalizacao(
                    nome=personalizacao.nome,
                    preco_adicional=personalizacao.preco_adicional,
                    categoria=personalizacao.categoria,
                    bebida_id=bebida.id
                )
                db.add(nova_pers)
    
    db.commit()

def create_clientes(db: Session):
    """Cria clientes de teste"""
    # Verificar se já existem clientes
    clientes_existentes = db.query(Cliente).count()
    if clientes_existentes > 0:
        print("⚠️ Clientes já existem no banco, pulando criação...")
        return db.query(Cliente).all()
    
    clientes = [
        Cliente(
            nome="João Silva",
            email="joao@email.com",
            senha_hash=hash_password("123456"),
            tipo_usuario=TipoUsuarioEnum.CLIENTE,
            pontos_fidelidade=150
        ),
        Cliente(
            nome="Maria Santos",
            email="maria@email.com",
            senha_hash=hash_password("123456"),
            tipo_usuario=TipoUsuarioEnum.CLIENTE,
            pontos_fidelidade=200
        ),
        Cliente(
            nome="Pedro Costa",
            email="pedro@email.com",
            senha_hash=hash_password("123456"),
            tipo_usuario=TipoUsuarioEnum.CLIENTE,
            pontos_fidelidade=50
        ),
        Cliente(
            nome="Ana Oliveira",
            email="ana@email.com",
            senha_hash=hash_password("123456"),
            tipo_usuario=TipoUsuarioEnum.CLIENTE,
            pontos_fidelidade=300
        ),
        # Usuário staff para administração
        Cliente(
            nome="Admin Staff",
            email="admin@cafeteria.com",
            senha_hash=hash_password("admin123"),
            tipo_usuario=TipoUsuarioEnum.STAFF,
            pontos_fidelidade=0
        ),
    ]
    
    for cliente in clientes:
        db.add(cliente)
    db.commit()
    return clientes

def create_pedidos_exemplo(db: Session, clientes: list, bebidas: list):
    """Cria alguns pedidos de exemplo"""
    import random
    from datetime import datetime, timedelta
    
    # Pega algumas bebidas e personalizações
    cafe_bebidas = [b for b in bebidas if b.tipo == TipoBebidasEnum.CAFE]
    cha_bebidas = [b for b in bebidas if b.tipo == TipoBebidasEnum.CHA]
    
    # Cria alguns pedidos históricos
    for i in range(10):
        cliente = random.choice(clientes)
        bebida = random.choice(cafe_bebidas + cha_bebidas)
        
        # Cria pedido
        pedido = Pedido(
            cliente_id=cliente.id,
            total=bebida.preco_base * random.randint(1, 3),
            desconto=0.0,
            total_final=bebida.preco_base * random.randint(1, 3),
            status=random.choice([
                StatusPedidoEnum.PENDENTE, 
                StatusPedidoEnum.RECEBIDO,
                StatusPedidoEnum.EM_PREPARO, 
                StatusPedidoEnum.PRONTO, 
                StatusPedidoEnum.ENTREGUE
            ]),
            metodo_pagamento=random.choice([MetodoPagamentoEnum.PIX, MetodoPagamentoEnum.CARTAO, MetodoPagamentoEnum.DINHEIRO]),
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
        )
        db.add(pedido)
        db.commit()
        
        # Cria item do pedido
        item = ItemPedido(
            pedido_id=pedido.id,
            bebida_id=bebida.id,
            quantidade=random.randint(1, 3),
            preco_unitario=bebida.preco_base,
            subtotal=bebida.preco_base * random.randint(1, 3)
        )
        db.add(item)
        
        # Histórico do pedido
        historico = HistoricoPedido(
            pedido_id=pedido.id,
            status_anterior=StatusPedidoEnum.PENDENTE,
            status_novo=pedido.status
        )
        db.add(historico)
    
    db.commit()

def run_seeds():
    """Executa todas as seeds"""
    # Inicializa o banco
    init_db()
    
    # Obtém sessão do banco
    db = next(get_db())
    
    try:
        print("🌱 Iniciando seeds...")
        
        # Cria bebidas
        print("📦 Criando bebidas...")
        bebidas = create_bebidas(db)
        
        # Cria personalizações
        print("🎨 Criando personalizações...")
        create_personalizacoes(db, bebidas)
        
        # Cria clientes
        print("👥 Criando clientes...")
        clientes = create_clientes(db)
        
        # Cria pedidos de exemplo
        print("🛒 Criando pedidos de exemplo...")
        create_pedidos_exemplo(db, clientes, bebidas)
        
        print("✅ Seeds executadas com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao executar seeds: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_seeds()
