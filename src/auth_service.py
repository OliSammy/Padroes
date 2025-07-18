"""
Controller de Autenticação com JWT
Sistema de Cafeteria - Padrões GoF
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Imports do nosso sistema
from DAO.config import get_db
from DAO.models import Cliente
from DAO.crud import ClienteRepository
from src.auth import (
    verify_password, get_password_hash, create_access_token, 
    verify_token, get_user_from_token, ACCESS_TOKEN_EXPIRE_MINUTES
)

# Router principal para autenticação
auth_router = APIRouter()

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
    tipo_usuario: str = "cliente"  # "cliente" ou "staff"
    
    class Config:
        json_schema_extra = {
            "example": {
                "nome": "João Silva",
                "email": "joao@email.com",
                "senha": "123456",
                "tipo_usuario": "cliente"
            }
        }

class UserResponse(BaseModel):
    """Schema para resposta do usuário"""
    id: int
    nome: str
    email: str
    tipo_usuario: str
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

# Dependências para verificar tipos de usuário
def get_current_staff_user(current_user: Cliente = Depends(get_current_user)) -> Cliente:
    """Verifica se o usuário atual é staff"""
    if current_user.tipo_usuario.value != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas usuários staff podem acessar este recurso."
        )
    return current_user

def get_current_client_user(current_user: Cliente = Depends(get_current_user)) -> Cliente:
    """Verifica se o usuário atual é cliente"""
    if current_user.tipo_usuario.value != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas clientes podem acessar este recurso."
        )
    return current_user

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

@auth_router.post("/register", response_model=Dict[str, Any])
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Registro de novo usuário
    
    Cria uma nova conta de usuário no sistema.
    """
    cliente_repo = ClienteRepository(db)
    
    # Verificar se email já existe
    if cliente_repo.get_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )
    
    # Verificar se nome já existe
    existing_user = db.query(Cliente).filter(Cliente.nome == user_data.nome).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome já cadastrado"
        )
    
    try:
        # Validar tipo de usuário
        if user_data.tipo_usuario not in ["cliente", "staff"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de usuário deve ser 'cliente' ou 'staff'"
            )
        
        # Criar hash da senha
        hashed_password = get_password_hash(user_data.senha)
        
        # Importar enum
        from DAO.models import TipoUsuarioEnum
        tipo_enum = TipoUsuarioEnum.STAFF if user_data.tipo_usuario == "staff" else TipoUsuarioEnum.CLIENTE
        
        # Criar cliente
        cliente = Cliente(
            nome=user_data.nome,
            email=user_data.email,
            senha_hash=hashed_password,
            tipo_usuario=tipo_enum,
            pontos_fidelidade=0
        )
        
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        
        # Criar token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": cliente.email, "user_id": cliente.id},
            expires_delta=access_token_expires
        )
        
        return {
            "message": "Usuário cadastrado com sucesso",
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": cliente.id,
                "nome": cliente.nome,
                "email": cliente.email,
                "tipo_usuario": cliente.tipo_usuario.value,
                "pontos_fidelidade": cliente.pontos_fidelidade
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar usuário: {str(e)}"
        )

@auth_router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login do usuário
    
    Autentica o usuário e retorna um token JWT.
    Aceita login por nome ou email.
    """
    
    # Autenticar usuário
    cliente = authenticate_user(db, credentials.identifier, credentials.senha)
    
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Criar token JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": cliente.email, "user_id": cliente.id},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            id=cliente.id,
            nome=cliente.nome,
            email=cliente.email,
            tipo_usuario=cliente.tipo_usuario.value,
            pontos_fidelidade=cliente.pontos_fidelidade
        )
    )

@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: Cliente = Depends(get_current_user)):
    """
    Obtém informações do usuário atual
    
    Retorna os dados do usuário logado baseado no token JWT.
    """
    return UserResponse(
        id=current_user.id,
        nome=current_user.nome,
        email=current_user.email,
        tipo_usuario=current_user.tipo_usuario.value,
        pontos_fidelidade=current_user.pontos_fidelidade
    )

@auth_router.post("/refresh")
async def refresh_token(current_user: Cliente = Depends(get_current_user)):
    """
    Renova o token JWT
    
    Gera um novo token para o usuário logado.
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

@auth_router.get("/")
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

@auth_router.get("/protected")
async def protected_endpoint(current_user: Cliente = Depends(get_current_user)):
    """Endpoint protegido para teste"""
    return {
        "message": f"Olá {current_user.nome}! Este é um endpoint protegido.",
        "user_id": current_user.id,
        "email": current_user.email,
        "timestamp": datetime.now()
    }

# Endpoint para listar todos os usuários (apenas para desenvolvimento)
@auth_router.get("/users", response_model=List[UserResponse])
async def list_users(db: Session = Depends(get_db)):
    """Lista todos os usuários (endpoint de desenvolvimento)"""
    users = db.query(Cliente).all()
    return [UserResponse.from_orm(user) for user in users]

# Endpoints específicos por tipo de usuário
@auth_router.get("/staff/dashboard")
async def staff_dashboard(current_staff: Cliente = Depends(get_current_staff_user)):
    """Dashboard específico para usuários staff"""
    return {
        "message": f"Bem-vindo ao painel administrativo, {current_staff.nome}!",
        "tipo_usuario": current_staff.tipo_usuario.value,
        "acesso": "staff",
        "recursos_disponiveis": [
            "Gerenciar pedidos",
            "Visualizar estatísticas",
            "Administrar produtos",
            "Configurar sistema"
        ]
    }

@auth_router.get("/client/menu")
async def client_menu(current_client: Cliente = Depends(get_current_client_user)):
    """Endpoints específico para clientes verem o cardápio"""
    return {
        "message": f"Olá {current_client.nome}! Aqui está seu cardápio personalizado.",
        "tipo_usuario": current_client.tipo_usuario.value,
        "acesso": "cliente",
        "pontos_fidelidade": current_client.pontos_fidelidade,
        "recursos_disponiveis": [
            "Ver cardápio",
            "Fazer pedidos", 
            "Personalizar bebidas",
            "Acompanhar pedidos"
        ]
    }

@auth_router.get("/user-type")
async def get_user_type(current_user: Cliente = Depends(get_current_user)):
    """Retorna o tipo do usuário logado"""
    return {
        "user_id": current_user.id,
        "nome": current_user.nome,
        "tipo_usuario": current_user.tipo_usuario.value,
        "is_staff": current_user.tipo_usuario.value == "staff",
        "is_client": current_user.tipo_usuario.value == "cliente"
    }

# Para compatibilidade, criar também uma versão app se necessário executar standalone
if __name__ == "__main__":
    from fastapi import FastAPI
    import uvicorn
    
    app = FastAPI(title="Sistema de Cafeteria - Auth", version="1.0.0")
    app.include_router(auth_router, prefix="/auth")
    uvicorn.run(app, host="0.0.0.0", port=8001)
