#!/bin/bash

# 🛑 Script de Parada do Sistema de Cafeteria
# ==========================================

echo "🛑 Parando Sistema de Cafeteria..."
echo "================================="

# Parar e remover containers
echo "📦 Parando containers..."
docker-compose down

# Verificar se containers foram parados
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Sistema parado com sucesso!"
    echo "============================="
    echo ""
    echo "💡 Para reiniciar o sistema:"
    echo "   ./start.sh"
    echo ""
    echo "🧹 Para limpar completamente (remover volumes):"
    echo "   docker-compose down -v"
    echo "   docker system prune -f"
    echo ""
else
    echo "❌ Erro ao parar containers"
    exit 1
fi
