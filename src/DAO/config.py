"""
Configuração do banco de dados SQLite
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Configuração do banco
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./cafeteria.db"
)

# Para SQLite, adicionar configurações específicas
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Necessário para SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Inicializa o banco criando todas as tabelas"""
    Base.metadata.create_all(bind=engine)
