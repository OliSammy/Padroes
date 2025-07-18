#!/bin/bash

# 🚀 Script de Inicialização do Sistema de Cafeteria
# ===============================================

echo "🏗️  Iniciando Sistema de Cafeteria..."
echo "======================================="

# Verificar se Docker está rodando
if ! docker info &> /dev/null; then
    echo "❌ Docker não está rodando. Por favor, inicie o Docker primeiro."
    exit 1
fi

# Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não encontrado. Por favor, instale o Docker Compose."
    exit 1
fi

echo "✅ Docker verificado com sucesso"

# Parar containers existentes (se houver)
echo "🛑 Parando containers existentes..."
docker-compose down &> /dev/null

# Construir e iniciar containers
echo "🏗️  Construindo e iniciando containers..."
docker-compose up --build -d

# Aguardar containers estarem prontos
echo "⏳ Aguardando containers ficarem prontos..."
sleep 10

# Verificar se a aplicação está rodando
echo "🔍 Verificando status da aplicação..."
if curl -f http://localhost:8000/ &> /dev/null; then
    echo ""
    echo "🎉 SUCESSO! Sistema inicializado com sucesso!"
    echo "==========================================="
    echo ""
    echo "🌐 Acesse os seguintes endereços:"
    echo "   • API Principal: http://localhost:8000"
    echo "   • Documentação:  http://localhost:8000/docs"
    echo "   • Demonstrações: http://localhost:8000/demo"
    echo ""
    echo "📱 Tipos de Usuário Disponíveis:"
    echo "   • CLIENTE: Para acesso ao cardápio"
    echo "   • STAFF:   Para dashboard administrativo"
    echo ""
    echo "🛑 Para parar o sistema, execute: ./stop.sh"
    echo ""
else
    echo "❌ Erro: A aplicação não está respondendo"
    echo "📋 Verificando logs..."
    docker-compose logs --tail=20
    exit 1
fi
