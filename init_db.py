#!/usr/bin/env python3
"""
Script para inicializar o banco de dados SQLite
Cria o banco e executa as seeds se necessário
"""
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.append(str(Path(__file__).parent))

from database.config import init_db, engine
from database.seeds import run_seeds
import sqlite3


def check_database_exists():
    """Verifica se o arquivo do banco de dados existe"""
    db_path = "cafeteria.db"
    return os.path.exists(db_path)


def check_tables_exist():
    """Verifica se as tabelas existem no banco"""
    try:
        with sqlite3.connect("cafeteria.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='clientes'
            """)
            return cursor.fetchone() is not None
    except Exception:
        return False


def get_database_info():
    """Obtém informações sobre o banco de dados"""
    try:
        with sqlite3.connect("cafeteria.db") as conn:
            cursor = conn.cursor()
            
            # Listar todas as tabelas
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            # Contar registros em algumas tabelas principais
            counts = {}
            main_tables = ['clientes', 'bebidas', 'personalizacoes', 'pedidos', 'itens_carrinho']
            
            for table in main_tables:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
            
            return tables, counts
    except Exception as e:
        return [], {"error": str(e)}


def main():
    """Função principal"""
    print("🏪 Inicializador do Banco de Dados - Sistema de Cafeteria")
    print("=" * 60)
    
    # Verificar se o banco existe
    db_exists = check_database_exists()
    tables_exist = check_tables_exist() if db_exists else False
    
    print(f"📁 Arquivo do banco: {'✅ Existe' if db_exists else '❌ Não existe'}")
    print(f"📋 Tabelas criadas: {'✅ Sim' if tables_exist else '❌ Não'}")
    
    if not db_exists or not tables_exist:
        print("\n🔧 Iniciando configuração do banco de dados...")
        
        try:
            # Inicializar banco (criar tabelas)
            print("📊 Criando tabelas...")
            init_db()
            print("✅ Tabelas criadas com sucesso!")
            
            # Executar seeds
            print("🌱 Executando seeds (dados iniciais)...")
            run_seeds()
            print("✅ Seeds executadas com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro durante a inicialização: {e}")
            return 1
    
    else:
        print("\n✅ Banco de dados já está configurado!")
    
    # Mostrar informações do banco
    print("\n📊 Informações do banco de dados:")
    tables, counts = get_database_info()
    
    if "error" in counts:
        print(f"❌ Erro ao obter informações: {counts['error']}")
    else:
        print(f"📋 Tabelas criadas ({len(tables)}): {', '.join(tables)}")
        print("\n📈 Registros por tabela:")
        for table, count in counts.items():
            print(f"   {table}: {count} registros")
    
    print("\n🎉 Sistema pronto para uso!")
    print("🚀 Execute: python main.py para iniciar o servidor")
    print("📖 Documentação: http://localhost:8000/docs")
    
    return 0


if __name__ == "__main__":
    exit(main())
