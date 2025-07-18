#!/bin/bash

# 🚀 Script de Configuração do Sistema de Cafeteria
# Automatiza a instalação e configuração do ambiente

set -e  # Para em caso de erro

echo "🏪 Configurando Sistema de Cafeteria - Padrões GoF"
echo "=================================================="

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor, instale Python 3.8 ou superior."
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"

# Criar ambiente virtual se não existir
if [ ! -d ".venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3 -m venv .venv
else
    echo "✅ Ambiente virtual já existe"
fi

# Ativar ambiente virtual
echo "🔧 Ativando ambiente virtual..."
source .venv/bin/activate

# Atualizar pip
echo "⬆️ Atualizando pip..."
pip install --upgrade pip

# Instalar dependências
echo "📥 Instalando dependências..."
pip install -r requirements.txt

# Criar arquivo .env se não existir
if [ ! -f ".env" ]; then
    echo "⚙️ Criando arquivo .env..."
    cat > .env << EOF
# Configurações do Sistema de Cafeteria
DATABASE_URL=sqlite:///./cafeteria.db
SECRET_KEY=sua_chave_secreta_aqui_$(date +%s)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True
EOF
else
    echo "✅ Arquivo .env já existe"
fi

echo ""
echo "🔧 Inicializando banco de dados..."
python init_db.py

echo ""
echo "🎉 Configuração concluída com sucesso!"
echo ""
echo "Para executar o sistema:"
echo "1️⃣ Ative o ambiente: source .venv/bin/activate"
echo "2️⃣ Execute o servidor: python main.py"
echo "3️⃣ Acesse: http://localhost:8000"
echo "4️⃣ Documentação: http://localhost:8000/docs"
echo ""
echo "Para testar os padrões:"
echo "🎯 Execute: python demo_padroes.py"
echo ""
echo "Bom desenvolvimento! 🚀"
