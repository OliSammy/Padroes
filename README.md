# 🏪 Sistema de Cafeteria

## 📋 Descrição do Projeto

Este projeto implementa um sistema de gerenciamento de pedidos para uma cafeteria.

### 🎯 Objetivos

- Implementar os 9 padrões (6 GoF + 3 arquiteturais)
- Demonstrar a integração e colaboração entre os padrões
- Criar um sistema funcional e bem estruturado
- Aplicar boas práticas de desenvolvimento

## � **Arquitetura e Estrutura**

### 🏗️ **Estrutura do Projeto**

```
sistema-cafeteria/
├── 📁 controllers/          # Controladores da API
├── 📁 database/            # Configuração e modelos do banco
├── 📁 patterns/            # Implementação dos padrões GoF
├── 📁 tests/              # Testes automatizados
├── 🐳 docker-compose.yml   # Configuração Docker
├── 🐳 Dockerfile          # Container da aplicação
├── 🚀 start.sh   # Scripts de inicialização
├── 🛑 stop.sh     # Scripts de parada
├── 📋 requirements.txt     # Dependências Python
├── 🗃️ cafeteria.db        # Banco de dados SQLite
└── 🚀 main.py             # Ponto de entrada da aplicação
```

### 🔧 **Tecnologias**

- **Backend**: Python 3.12+
- **Framework Web**: FastAPI
- **Banco de Dados**: SQLite com SQLAlchemy ORM
- **Autenticação**: JWT + BCrypt para segurança completa
- **Autorização**: Sistema de tipos de usuário (Cliente/Staff)
- **Documentação**: Swagger/OpenAPI automático
- **Ambiente**: Virtual Environment (venv)
- **Containerização**: Docker + Docker Compose

## 🎨 Padrões Implementados

### 🔹 Padrões GoF

#### 1. **Decorator Pattern** 🎨
- **Localização**: `patterns/decorator.py`
- **Aplicação**: Personalização dinâmica de bebidas
- **Exemplo**: Café + Leite de Aveia + Canela + Sem Açúcar
- **Benefício**: Combinações infinitas sem explosão de classes

```python
cafe = Cafe()
cafe_personalizado = LeiteDeAveia(cafe)
cafe_personalizado = Canela(cafe_personalizado)
cafe_personalizado = SemAcucar(cafe_personalizado)
```

#### 2. **Observer Pattern** 👁️
- **Localização**: `patterns/observer.py`
- **Aplicação**: Notificações automáticas para cozinha e cliente
- **Exemplo**: Mudança de status → Notifica todos os interessados
- **Benefício**: Baixo acoplamento, notificações automáticas

```python
pedido = PedidoSubject(123)
pedido.adicionar_observer(CozinhaObserver())
pedido.adicionar_observer(ClienteObserver())
pedido.notificar_observers()  # Todos são notificados
```

#### 3. **Strategy Pattern** 💰
- **Localização**: `patterns/strategy.py`
- **Aplicação**: Diferentes políticas de desconto no pagamento
- **Exemplo**: PIX (5%), Fidelidade (10%), Cartão (0%)
- **Benefício**: Algoritmos intercambiáveis, extensibilidade

```python
contexto = ContextoPagamento()
contexto.set_strategy(DescontoPix())  # 5% desconto
total = contexto.calcular_total(valor_original)
```

#### 4. **Factory Method Pattern** 🏭
- **Localização**: `patterns/factory.py`
- **Aplicação**: Criação de bebidas base (Café, Chá, Chocolate, Suco)
- **Exemplo**: MenuFactory cria bebidas conforme o tipo
- **Benefício**: Encapsula criação, facilita extensão

```python
factory = MenuFactory()
cafe = factory.criar_bebida("cafe", "Espresso")
cha = factory.criar_bebida("cha", "Chá Verde")
```

#### 5. **Command Pattern** ⚡
- **Localização**: `patterns/command.py`
- **Aplicação**: Encapsulamento de ações (criar, cancelar, alterar pedidos)
- **Exemplo**: Suporte a undo/redo, logging de ações
- **Benefício**: Ações como objetos, histórico, reversibilidade

```python
interface = InterfaceUsuario()
interface.criar_pedido(bebida)
interface.cancelar_pedido(123)
interface.desfazer_ultimo_comando()  # Undo
```

#### 6. **State Pattern** 🔄
- **Localização**: `patterns/state.py`
- **Aplicação**: Gerenciamento de estados do pedido
- **Exemplo**: Pendente → Em Preparo → Pronto → Entregue
- **Benefício**: Transições controladas, comportamento específico por estado

```python
pedido = Pedido(123)
pedido.avancar_estado()  # Recebido → Em Preparo
pedido.avancar_estado()  # Em Preparo → Pronto
```

### 🔹 Padrões Arquiteturais

#### 7. **DAO/Repository Pattern** 🗄️
- **Localização**: `database/repositories.py`
- **Aplicação**: Isolamento do acesso a dados
- **Exemplo**: ClienteRepository, PedidoRepository, BebidaRepository
- **Benefício**: Abstração da persistência, testabilidade

#### 8. **Business Object (BO) Pattern** 💼
- **Localização**: `patterns/business_object.py`
- **Aplicação**: Encapsulamento da lógica de negócio
- **Exemplo**: PedidoBO, ClienteBO, ProdutoBO
- **Benefício**: Centralização das regras de negócio, reutilização

#### 9. **Model-View-Controller (MVC)** 🖥️
- **Localização**: `controllers/`, `database/models.py`, `main.py`
- **Aplicação**: Separação de responsabilidades
- **Exemplo**: Controllers para API, Models para dados, Views via FastAPI
- **Benefício**: Organização, manutenibilidade, separação de camadas

## 📁 Estrutura do Projeto

```
cafeteria/
├── controllers/                 # 🎮 Controllers (MVC)
│   ├── auth_controller.py      # Autenticação e registro
│   ├── carrinho_controller.py  # Gerenciamento do carrinho
│   ├── pedido_controller.py    # Gerenciamento de pedidos
│   └── personalizacao_controller.py # Personalização de bebidas
│
├── database/                   # 🗄️ Camada de dados
│   ├── config.py              # Configuração do banco
│   ├── models.py              # Modelos SQLAlchemy
│   ├── repositories.py        # Repositórios (DAO)
│   └── seeds.py               # Dados iniciais
│
├── patterns/                   # 🎨 Padrões GoF
│   ├── decorator.py           # Decorator Pattern
│   ├── observer.py            # Observer Pattern  
│   ├── strategy.py            # Strategy Pattern
│   ├── factory.py             # Factory Method
│   ├── command.py             # Command Pattern
│   ├── state.py               # State Pattern
│   └── business_object.py     # Business Object
│
├── main.py                     # 🚀 Aplicação principal
├── demo_padroes.py            # 🎯 Demonstração dos padrões
├── requirements.txt           # 📦 Dependências
├── .env                       # ⚙️ Configurações
└── README.md                  # 📚 Documentação
```

## 🚀 Como Executar

### 🐳 **Execução com Docker (Recomendado)**

**Pré-requisitos:**
- Docker e Docker Compose instalados

```bash
# Iniciar com Docker Compose (uma linha!)
./start.sh

# Parar o sistema
./stop.sh
```

**Após executar:**
- **API**: <http://localhost:8000>
- **Documentação**: <http://localhost:8000/docs>
- **Demonstrações**: <http://localhost:8000/demo>

### 💻 **Execução Manual (Desenvolvimento)**

**Pré-requisitos:**

- Python 3.12+
- pip (gerenciador de pacotes)

### 1. **Preparar Ambiente**

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 2. **Configurar Banco de Dados**

```bash
# O banco SQLite será criado automaticamente
# Configurações estão no arquivo .env
DATABASE_URL=sqlite:///./cafeteria.db
```

### 3. **Executar Aplicação**

```bash
# Iniciar servidor
python main.py

# Ou usando uvicorn diretamente
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. **Acessar Sistema**

- **API**: http://localhost:8000
- **Documentação**: http://localhost:8000/docs
- **Demonstrações**: http://localhost:8000/demo

### 5. **Executar Demonstração dos Padrões**

```bash
# Executar demonstração completa
python demo_padroes.py
```

## 📋 Funcionalidades Principais

### 🔐 **Sistema de Autenticação e Autorização**

#### **Autenticação JWT**
- Registro e login de usuários
- Tokens JWT com expiração automática (30 minutos)
- Hash seguro de senhas com BCrypt
- Refresh token para renovação automática

#### **Sistema de Tipos de Usuário**
O sistema implementa dois tipos de usuário com permissões distintas:

##### 👤 **CLIENTE**
- Acesso ao cardápio personalizado
- Gerenciamento do próprio carrinho
- Criação e acompanhamento de pedidos
- Personalização de bebidas
- Sistema de pontos de fidelidade
- **Endpoints exclusivos:**
  - `GET /auth/client/menu` - Cardápio personalizado
  - `GET /carrinho` - Visualizar carrinho
  - `POST /carrinho` - Adicionar itens
  - `GET /pedidos` - Pedidos do cliente
  - `POST /pedidos` - Criar novo pedido

##### 👨‍💼 **STAFF**
- Acesso ao dashboard administrativo
- Gerenciamento de todos os pedidos
- Visualização de estatísticas do sistema
- Administração de produtos e cardápio
- Configurações do sistema
- **Endpoints exclusivos:**
  - `GET /auth/staff/dashboard` - Painel administrativo
  - Futuros endpoints de administração

#### **Registro de Usuários**

**Registrar Cliente:**
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "João Silva",
    "email": "joao@email.com", 
    "senha": "123456",
    "tipo_usuario": "cliente"
  }'
```

**Registrar Staff:**
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Admin Sistema",
    "email": "admin@cafeteria.com",
    "senha": "admin123", 
    "tipo_usuario": "staff"
  }'
```

#### **Login e Verificação**

**Login (qualquer tipo):**
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "joao@email.com",
    "senha": "123456"
  }'
```

**Verificar tipo do usuário logado:**
```bash
curl -X GET "http://localhost:8000/auth/user-type" \
  -H "Authorization: Bearer SEU_TOKEN_JWT"
```

**Resposta incluirá:**
```json
{
  "user_id": 1,
  "nome": "João Silva",
  "tipo_usuario": "cliente",
  "is_staff": false,
  "is_client": true
}
```

### 🛒 **Carrinho de Compras**
- Adicionar bebidas ao carrinho
- Personalizar bebidas (Decorator Pattern)
- Calcular totais automaticamente

### 📋 **Gerenciamento de Pedidos**
- Criar pedidos a partir do carrinho
- Acompanhar status em tempo real (State Pattern)
- Notificações automáticas (Observer Pattern)

### 💰 **Sistema de Pagamento**
- Diferentes métodos de pagamento
- Aplicação automática de descontos (Strategy Pattern)
- Suporte a múltiplas políticas de desconto

### 👨‍🍳 **Interface da Cozinha**
- Visualizar pedidos pendentes
- Alterar status dos pedidos
- Notificações automáticas

## 🎯 Demonstrações Disponíveis

### 📡 **Endpoints da API**

```http
# Autenticação e Autorização
POST /auth/register          # Registro (cliente ou staff)
POST /auth/login             # Login universal  
GET  /auth/me               # Informações do usuário logado
GET  /auth/user-type        # Verificar tipo de usuário
POST /auth/refresh          # Renovar token JWT

# Endpoints Específicos por Tipo
GET  /auth/client/menu      # Cardápio personalizado (APENAS CLIENTES)
GET  /auth/staff/dashboard  # Dashboard administrativo (APENAS STAFF)

# Bebidas e Personalização
GET  /bebidas
GET  /personalizacoes
POST /personalizacoes/personalizar  # Requer autenticação

# Carrinho (APENAS CLIENTES autenticados)
GET  /carrinho
POST /carrinho
PUT  /carrinho/{id}
DELETE /carrinho/{id}

# Pedidos (APENAS CLIENTES autenticados)
GET  /pedidos
POST /pedidos
PATCH /pedidos/{id}/status
GET  /pedidos/cozinha/pendentes

# Demonstrações (Públicas)
GET  /demo
GET  /demo/decorator
GET  /demo/observer
```

### 🎮 **Demonstração dos Padrões**

Execute `python demo_padroes.py` para ver:

1. **Decorator**: Personalização step-by-step de bebidas
2. **Factory**: Criação de diferentes tipos de bebidas
3. **Strategy**: Aplicação de diferentes descontos
4. **Observer**: Notificações em tempo real
5. **State**: Transições de estado do pedido
6. **Command**: Execução e reversão de ações
7. **Integração**: Todos os padrões trabalhando juntos

## 🧪 Exemplos de Uso

### **Exemplo 1: Personalização de Bebida (Decorator)**

```python
from patterns.decorator import Cafe, LeiteDeAveia, Canela, SemAcucar

# Criar bebida base
cafe = Cafe()  # R$ 3.50

# Aplicar personalizações
bebida = LeiteDeAveia(cafe)     # + R$ 1.00
bebida = Canela(bebida)         # + R$ 0.50  
bebida = SemAcucar(bebida)      # + R$ 0.00

print(bebida.get_descricao())   # "Café com Leite de Aveia com Canela sem Açúcar"
print(bebida.get_preco())       # R$ 5.00
```

### **Exemplo 2: Processo Completo de Pedido**

```python
# 1. Criar bebida personalizada (Factory + Decorator)
factory = MenuFactory()
cafe = factory.criar_bebida("cafe")
cafe_especial = LeiteDeAveia(Canela(cafe))

# 2. Adicionar ao carrinho via BO
cliente_bo = ClienteBO(db)
cliente_bo.adicionar_ao_carrinho(cliente_id=1, bebida_id=1, personalizacoes=[1,2])

# 3. Criar pedido (Command + Observer + Strategy)
pedido_bo = PedidoBO(db)
pedido_id = pedido_bo.criar_pedido(
    cliente_id=1, 
    metodo_pagamento=MetodoPagamentoEnum.PIX,
    tipo_desconto=TipoDescontoEnum.PIX
)

# 4. Processar na cozinha (State + Observer)
pedido_bo.alterar_status(pedido_id, StatusPedidoEnum.EM_PREPARO)
pedido_bo.alterar_status(pedido_id, StatusPedidoEnum.PRONTO)
pedido_bo.alterar_status(pedido_id, StatusPedidoEnum.ENTREGUE)
```

## 🔍 Aspectos Técnicos

### **Banco de Dados**
- SQLite para simplicidade
- SQLAlchemy ORM para abstração
- Relacionamentos bem definidos
- Seeds automáticas para testes

### **API REST**
- FastAPI para performance e produtividade
- Documentação automática com Swagger
- Validação automática com Pydantic
- CORS configurado para frontends

### **Arquitetura**
- Separation of Concerns
- Dependency Injection
- Repository Pattern para dados
- Business Objects para lógica

### **Qualidade de Código**
- Type hints em todo o código
- Documentação em português
- Tratamento de erros abrangente
- Logging adequado

## 👥 Benefícios dos Padrões Implementados

### **Para Desenvolvimento:**
- ✅ Código mais organizado e legível
- ✅ Facilidade de manutenção e evolução
- ✅ Reutilização de componentes
- ✅ Testabilidade melhorada

### **Para o Negócio:**
- ✅ Flexibilidade na personalização
- ✅ Facilidade para adicionar novos produtos
- ✅ Gestão automática de estados
- ✅ Notificações em tempo real

### **Para Extensibilidade:**
- ✅ Novos tipos de bebidas (Factory)
- ✅ Novas personalizações (Decorator)
- ✅ Novos tipos de desconto (Strategy)
- ✅ Novos observadores (Observer)
- ✅ Novos comandos (Command)
- ✅ Novos estados (State)

## � **Docker - Comandos Úteis**

### 🔍 **Monitoramento**

```bash
# Ver logs em tempo real
docker-compose logs -f

# Ver apenas logs da aplicação
docker-compose logs -f app

# Verificar status dos containers
docker-compose ps

# Verificar uso de recursos
docker stats
```

### 🧹 **Limpeza e Manutenção**

```bash
# Parar e remover tudo (mantém volumes)
docker-compose down

# Remover tudo incluindo volumes (⚠️ apaga dados!)
docker-compose down -v

# Limpar imagens não utilizadas
docker system prune -f

# Rebuild completo da aplicação
docker-compose up --build --force-recreate
```

### 🐛 **Debugging**

```bash
# Acessar shell do container
docker-compose exec app bash

# Executar comando no container
docker-compose exec app python -c "print('Hello!')"

# Ver configuração aplicada
docker-compose config
```

---
