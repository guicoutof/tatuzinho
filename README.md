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

2. **Inicie os serviços com Docker (Redis):**
```bash
make up
```

3. **Inicie o servidor de desenvolvimento:**
```bash
make start-dev
```

### Comandos disponíveis

- `make start-dev` - Inicia o servidor em modo desenvolvimento com reload automático
- `make start` - Inicia o servidor em produção
- `make up` - Inicia os containers Docker (Redis)
- `make down` - Para os containers Docker
- `make install-deps` - Instala as dependências Python

### Variáveis de ambiente

Copie o arquivo `.env.example` para `.env` e configure conforme necessário:

```bash
cp .env.example .env
```

### Detalhes do banco de dados

O projeto utiliza **Supabase** (PostgreSQL gerenciado).

- **Host:** db.ljctyleqgpecezgtulhf.supabase.co
- **Porta:** 5432
- **Banco:** postgres

> Configure a `DATABASE_URL` no arquivo `.env` com suas credenciais.

### Estrutura do projeto

```
tatuzinho/
├── app/
│   ├── __init__.py
│   ├── main.py          # Aplicação FastAPI
│   └── database.py      # Configuração do banco de dados
├── docker-compose.yml   # Configuração do Redis
├── requirements.txt     # Dependências Python
└── Makefile            # Comandos úteis
```
