# Tatuzinho

## Configuração com Docker

### Pré-requisitos
- Docker
- Docker Compose
- Python 3.12+

### Instalação

1. **Instale as dependências:**
```bash
make install-deps
```

2. **Inicie o PostgreSQL com Docker:**
```bash
make docker-up
```

3. **Inicie o servidor de desenvolvimento:**
```bash
make start-dev
```

### Comandos disponíveis

- `make start-dev` - Inicia o servidor em modo desenvolvimento com reload automático
- `make start` - Inicia o servidor em produção
- `make docker-up` - Inicia o container PostgreSQL
- `make docker-down` - Para o container PostgreSQL
- `make docker-logs` - Visualiza os logs do PostgreSQL
- `make install-deps` - Instala as dependências Python

### Variáveis de ambiente

Copie o arquivo `.env.example` para `.env` e configure conforme necessário:

```bash
cp .env.example .env
```

### Detalhes do banco de dados

- **Host:** localhost
- **Porta:** 5432
- **Usuário:** postgres
- **Senha:** postgres
- **Banco:** tatuzinho_db

### Estrutura do projeto

```
tatuzinho/
├── app/
│   ├── __init__.py
│   ├── main.py          # Aplicação FastAPI
│   └── database.py      # Configuração do banco de dados
├── docker-compose.yml   # Configuração do PostgreSQL
├── requirements.txt     # Dependências Python
└── Makefile            # Comandos úteis
```
