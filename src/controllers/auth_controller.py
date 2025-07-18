
"""
Controller de Autenticação com JWT
Sistema de Cafeteria - Padrões GoF
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Imports do nosso sistema
from database.config import get_db
from database.models import Cliente
from database.repositories import ClienteRepository
from patterns.business_object import ProdutoBO, PedidoBO
from patterns.business_object import ClienteBO
from src.auth import (
    verify_password, get_password_hash, create_access_token, 
    verify_token, get_user_from_token, ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="Sistema de Cafeteria - Auth", version="1.0.0")

# CORS para permitir frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração de segurança
security = HTTPBearer()

# Esquemas Pydantic para Autenticação
class UserLogin(BaseModel):
    """Schema para login - aceita tanto nome quanto email"""
    identifier: str  # Pode ser nome ou email
    senha: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "identifier": "joao@email.com",  # ou "João Silva"
                "senha": "123456"
            }
        }

class UserRegister(BaseModel):
    """Schema para registro"""
    nome: str
    email: EmailStr
    senha: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "nome": "João Silva",
                "email": "joao@email.com",
                "senha": "123456"
            }
        }

class UserResponse(BaseModel):
    """Schema para resposta do usuário"""
    id: int
    nome: str
    email: str
    pontos_fidelidade: int = 0
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    """Schema para token de resposta"""
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse

# Dependência para obter usuário atual
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Cliente:
    """Obtém o usuário atual a partir do token JWT"""
    
    token = credentials.credentials
    
    # Verificar e decodificar token
    try:
        email = get_user_from_token(token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Buscar usuário no banco
    cliente_repo = ClienteRepository(db)
    cliente = cliente_repo.get_by_email(email)
    
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return cliente

# Função auxiliar para autenticar por nome ou email
def authenticate_user(db: Session, identifier: str, password: str) -> Optional[Cliente]:
    """Autentica usuário por nome ou email"""
    cliente_repo = ClienteRepository(db)
    
    # Primeiro tenta por email
    cliente = cliente_repo.get_by_email(identifier)
    
    # Se não encontrou, tenta por nome
    if not cliente:
        cliente = db.query(Cliente).filter(Cliente.nome == identifier).first()
    
    # Verifica senha
    if cliente and verify_password(password, cliente.senha_hash):
        return cliente
    
    return None

# ENDPOINTS DE AUTENTICAÇÃO

@app.post("/auth/register", response_model=Dict[str, Any])
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Registro de novo usuário
    """
    bo = ClienteBO(db)
    result = bo.registrar_cliente_dict(user_data.nome, user_data.email, user_data.senha)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    # Criar token JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": result["email"], "user_id": result["id"]},
        expires_delta=access_token_expires
    )
    return {
        "message": "Usuário cadastrado com sucesso",
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": result
    }

@app.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login do usuário
    """
    bo = ClienteBO(db)
    user_dict = bo.autenticar_cliente_dict(credentials.identifier, credentials.senha)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_dict["email"], "user_id": user_dict["id"]},
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user_dict
    }

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: Cliente = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Obtém informações do usuário atual
    """
    bo = ClienteBO(db)
    return bo.cliente_response_dict(current_user)

@app.post("/auth/refresh")
async def refresh_token(current_user: Cliente = Depends(get_current_user)):
    """
    Renova o token JWT
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.email, "user_id": current_user.id},
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

# ENDPOINTS DE TESTE (Protegidos)

@app.get("/")
async def root():
    """Endpoint raiz público"""
    return {
        "message": "🏪 Sistema de Cafeteria - API de Autenticação",
        "version": "1.0.0",
        "endpoints": {
            "register": "/auth/register",
            "login": "/auth/login", 
            "user_info": "/auth/me",
            "refresh": "/auth/refresh"
        }
    }

@app.get("/auth/protected")
async def protected_endpoint(current_user: Cliente = Depends(get_current_user)):
    """Endpoint protegido para teste"""
    return {
        "message": f"Olá {current_user.nome}! Este é um endpoint protegido.",
        "user_id": current_user.id,
        "email": current_user.email,
        "timestamp": datetime.now()
    }

# Endpoint para listar todos os usuários (apenas para desenvolvimento)
@app.get("/auth/users", response_model=List[UserResponse])
async def list_users(db: Session = Depends(get_db)):
    """Lista todos os usuários (endpoint de desenvolvimento)"""
    users = db.query(Cliente).all()
    return [UserResponse.from_orm(user) for user in users]

@app.get("/bebidas")
async def listar_bebidas(db: Session = Depends(get_db)):
    """Lista todas as bebidas disponíveis"""
    bo = ProdutoBO(db)
    return bo.listar_bebidas_dict()

@app.get("/bebidas/{bebida_id}")
async def obter_bebida(bebida_id: int, db: Session = Depends(get_db)):
    """Obtém uma bebida específica"""
    bo = ProdutoBO(db)
    bebida_dict = bo.obter_bebida_dict(bebida_id)
    if not bebida_dict:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bebida não encontrada")
    return bebida_dict

@app.get("/bebidas/{bebida_id}/personalizacoes")
async def listar_personalizacoes(bebida_id: int, db: Session = Depends(get_db)):
    """Lista personalizações para uma bebida"""
    bo = ProdutoBO(db)
    return bo.listar_personalizacoes_bebida_dict(bebida_id)

@app.get("/carrinho")
async def obter_carrinho(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Obtém itens do carrinho do usuário"""
    bo = ClienteBO(db)
    return bo.obter_carrinho_dict(current_user.id)

@app.post("/carrinho")
async def adicionar_ao_carrinho(
    bebida_id: int,
    quantidade: int = 1,
    personalizacoes: list = None,
    observacoes: str = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adiciona item ao carrinho"""
    bo = ClienteBO(db)
    return bo.adicionar_ao_carrinho_dict(current_user.id, bebida_id, quantidade, personalizacoes, observacoes)

@app.delete("/carrinho/{item_id}")
async def remover_do_carrinho(
    item_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove item do carrinho"""
    bo = ClienteBO(db)
    result = bo.remover_item_carrinho_dict(item_id, current_user.id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado no carrinho")
    return result

@app.delete("/carrinho")
async def limpar_carrinho(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Limpa o carrinho do usuário"""
    bo = ClienteBO(db)
    return bo.limpar_carrinho_dict(current_user.id)

@app.get("/carrinho/total")
async def obter_total_carrinho(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém total do carrinho"""
    bo = ClienteBO(db)
    total = bo.obter_total_carrinho(current_user.id)
    return {"total": total}

@app.post("/pedidos")
async def criar_pedido(
    metodo_pagamento: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cria um novo pedido"""
    bo = PedidoBO(db)
    return bo.criar_pedido_completo(current_user.id, metodo_pagamento)

@app.get("/pedidos")
async def listar_pedidos(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista pedidos do usuário"""
    bo = PedidoBO(db)
    return bo.listar_pedidos_dict(current_user.id, None, 0, 50)

@app.get("/pedidos/{pedido_id}")
async def obter_pedido(
    pedido_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém um pedido específico"""
    bo = PedidoBO(db)
    pedido_dict = bo.obter_pedido_detalhado_dict(pedido_id)
    if not pedido_dict:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    if pedido_dict.get("cliente_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    return pedido_dict

# Cozinha (endpoints administrativos)
@app.get("/cozinha/pedidos")
async def listar_pedidos_cozinha(db: Session = Depends(get_db)):
    """Lista pedidos para a cozinha"""
    pedido_repo = PedidoRepository(db)
    pedidos = pedido_repo.get_pedidos_cozinha()
    
    return [
        {
            "id": pedido.id,
            "cliente": pedido.cliente.nome,
            "status": pedido.status.value,
            "total": pedido.total_final,
            "data_pedido": pedido.data_pedido,
            "itens_count": len(pedido.itens)
        }
        for pedido in pedidos
    ]

@app.patch("/cozinha/pedidos/{pedido_id}/status")
async def atualizar_status_pedido(
    pedido_id: int,
    novo_status: str,
    db: Session = Depends(get_db)
):
    """Atualiza status de um pedido"""
    pedido_repo = PedidoRepository(db)
    
    try:
        status_enum = StatusPedidoEnum(novo_status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status inválido"
        )
    
    if pedido_repo.update_status(pedido_id, status_enum):
        return {"message": "Status atualizado com sucesso"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado"
        )

# Estatísticas
@app.get("/stats")
async def obter_estatisticas(db: Session = Depends(get_db)):
    """Obtém estatísticas do sistema"""
    pedido_repo = PedidoRepository(db)
    cliente_repo = ClienteRepository(db)
    bebida_repo = BebidaRepository(db)
    
    stats = pedido_repo.get_estatisticas()
    
    return {
        "pedidos": stats,
        "clientes_total": len(cliente_repo.get_all()),
        "bebidas_disponiveis": len(bebida_repo.get_disponiveis()),
        "timestamp": datetime.now()
    }



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
