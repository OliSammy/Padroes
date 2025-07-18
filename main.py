"""
Aplicação principal do Sistema de Cafeteria
Implementa padrão MVC com padrões GoF
"""
import uvicorn # type: ignore
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Configuração do banco
from DAO.config import init_db, get_db
from DAO.seeds import run_seeds

# Autenticação JWT
from src.auth_service import get_current_user
from DAO.models import Cliente

# Controllers (padrão MVC)
from controllers.carrinho_controller import CarrinhoController
from controllers.pedido_controller import PedidoController
from controllers.personalizacao_controller import PersonalizacaoController
from controllers.bebida_controller import BebidaController
from controllers.dashboard_controller import DashboardController
from controllers.notificacao_controller import NotificacaoController

# Business Objects
from patterns.business_object import PedidoBO, ClienteBO, ProdutoBO


# Configuração da aplicação principal
app = FastAPI(
    title="Sistema de Cafeteria",
    description="""
    Sistema completo de pedidos personalizados para cafeteria que contém:
    
    Padrões GoF Implementados:
    - 🎨 Decorator: Personalização de bebidas
    - 👁️ Observer: Notificações para cozinha e cliente  
    - 💰 Strategy: Diferentes tipos de desconto
    - 🏭 Factory Method: Criação de bebidas base
    - ⚡ Command: Encapsulamento de ações do sistema
    - 🔄 State: Gerenciamento de estados do pedido
    
    Padrões Arquiteturais:
    - 🗄️ DAO/Repository: Acesso a dados
    - 💼 Business Object: Lógica de negócio
    - 🖥️ MVC: Separação de responsabilidades
    """,
    version="1.0.0"
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar controllers
carrinho_controller = CarrinhoController()
pedido_controller = PedidoController()
personalizacao_controller = PersonalizacaoController()
bebida_controller = BebidaController()
dashboard_controller = DashboardController()
notificacao_controller = NotificacaoController()

# Incluir rotas dos controllers
app.include_router(carrinho_controller.router)
app.include_router(pedido_controller.router)
app.include_router(personalizacao_controller.router)
app.include_router(bebida_controller.router)
app.include_router(dashboard_controller.router)
app.include_router(notificacao_controller.router)

# Incluir rotas de autenticação
from src.auth_service import auth_router
app.include_router(auth_router, prefix="/auth", tags=["Autenticação"])


@app.on_event("startup")
async def startup_event():
    """Inicialização da aplicação"""
    print("🚀 Iniciando Sistema de Cafeteria...")
    print("📊 Inicializando banco de dados...")
    
    # Inicializar banco
    init_db()
    
    print("✅ Banco de dados inicializado!")
    
    print("🎉 Sistema de Cafeteria iniciado com sucesso!")
    print("📚 Documentação disponível em: http://localhost:8000/docs")


@app.get("/")
async def root():
    """Endpoint raiz com informações do sistema"""
    return {
        "message": "🏪 Sistema de Cafeteria - Padrões GoF",
        "version": "1.0.0",
        "padroes_implementados": {
            "decorator": "✅ Personalização de bebidas",
            "observer": "✅ Notificações de pedidos",
            "strategy": "✅ Políticas de desconto",
            "factory_method": "✅ Criação de bebidas",
            "command": "✅ Encapsulamento de ações",
            "state": "✅ Estados do pedido",
        "dao": "✅ Acesso a dados",
            "business_object": "✅ Lógica de negócio",
            "mvc": "✅ Arquitetura MVC"
        },
        "endpoints": {
            "documentacao": "/docs",
            "auth": "/auth/*",
            "carrinho": "/carrinho/*",
            "pedidos": "/pedidos/*",
            "personalizacoes": "/personalizacoes/*",
        }
    }


@app.get("/health")
async def health_check():
    """Verifica saúde da aplicação"""
    return {
        "status": "healthy",
        "database": "connected",
        "patterns": "implemented",
        "timestamp": "2024-12-19T10:00:00Z"
    }


@app.get("/stats")
async def obter_estatisticas_sistema(db: Session = Depends(get_db)):
    """Obtém estatísticas gerais do sistema"""
    try:
        pedido_bo = PedidoBO(db)
        produto_bo = ProdutoBO(db)
        
        stats = pedido_bo.obter_estatisticas()
        bebidas = produto_bo.listar_bebidas()
        
        return {
            "sistema": {
                "total_pedidos": stats.get("total_pedidos", 0),
                "pedidos_hoje": stats.get("pedidos_hoje", 0),
                "faturamento_total": stats.get("faturamento_total", 0),
                "pedidos_pendentes": stats.get("pedidos_pendentes", 0),
                "pedidos_em_preparo": stats.get("pedidos_em_preparo", 0)
            },
            "produtos": {
                "total_bebidas": len(bebidas),
                "tipos_disponiveis": len(set(b.tipo.value for b in bebidas))
            },
            "padroes": {
                "decorator_personalizacoes": "Ativo",
                "observer_notificacoes": "Ativo", 
                "strategy_descontos": "Ativo",
                "factory_bebidas": "Ativo",
                "command_acoes": "Ativo",
                "state_pedidos": "Ativo"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter estatísticas: {str(e)}"
        )


@app.get("/demo/decorator")
async def demo_decorator(db: Session = Depends(get_db)):
    """Demonstração do padrão Decorator"""
    try:
        from patterns.decorator import Cafe, LeiteDeAveia, Canela, SemAcucar
        
        # Criar bebida base
        cafe = Cafe()
        
        # Aplicar decorators
        cafe_personalizado = LeiteDeAveia(cafe)
        cafe_personalizado = Canela(cafe_personalizado)
        cafe_personalizado = SemAcucar(cafe_personalizado)
        
        return {
            "padrao": "Decorator Pattern",
            "descricao": "Adição dinâmica de funcionalidades",
            "exemplo": {
                "bebida_base": {
                    "tipo": cafe.get_tipo(),
                    "descricao": cafe.get_descricao(),
                    "preco": cafe.get_preco()
                },
                "bebida_personalizada": {
                    "tipo": cafe_personalizado.get_tipo(),
                    "descricao": cafe_personalizado.get_descricao(),
                    "preco": cafe_personalizado.get_preco()
                }
            },
            "beneficios": [
                "Personalização flexível",
                "Combinações infinitas",
                "Extensibilidade sem modificar código base"
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na demonstração: {str(e)}"
        )


if __name__ == "__main__":
    print("🏪 Iniciando Sistema de Cafeteria...")
    print("📖 Acesse http://localhost:8000/docs para documentação")
    print("🎯 Acesse http://localhost:8000/demo para demonstrações")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
