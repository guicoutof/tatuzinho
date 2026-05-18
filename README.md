# Tatuzinho - Football Analytics API

API de análise de partidas de futebol com previsão de resultados usando modelo estatístico **Poisson**. Alimentada por dados históricos do [StatsBomb Open Data](https://github.com/statsbomb/open-data).

## Stack

- **Python 3.12+** / **FastAPI**
- **PostgreSQL** via **Supabase** (ou Docker local)
- **Redis** para cache
- **SQLAlchemy 2.0** (ORM)
- **Pydantic v2** (schemas)
- **Docker Compose** (PostgreSQL + Redis)

## Arquitetura em Camadas

```
HTTP Request
    ↓
Routers (app/routers/)
  - Validação de request
  - Mapeamento HTTP
  - Dependency injection
    ↓
Services (app/services/)
  - Lógica de negócio
  - Orquestração
    ↓
Repositories (app/repositories/)
  - Queries no banco
  - Abstração de dados
    ↓
Models (app/models.py)
  - Definições SQLAlchemy ORM
```

## Pré-requisitos

- Docker e Docker Compose
- Python 3.12+
- Make

## Instalação

```bash
# 1. Clone e entre no diretório
git clone <repo> && cd tatuzinho

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais (Supabase ou PostgreSQL local)

# 3. Instale dependências Python
make install-deps

# 4. Inicie os serviços Docker (PostgreSQL + Redis)
make up

# 5. Inicie o servidor de desenvolvimento
make start-dev
```

Acesse a documentação interativa em http://localhost:8000/docs

## Comandos

| Comando | Descrição |
|---|---|
| `make dev` | Sobe containers + servidor dev (reload automático) |
| `make prod` | Servidor produção |
| `make up` | Sobe containers Docker (PostgreSQL + Redis) |
| `make down` | Para containers Docker |
| `make install-deps` | Instala dependências Python |
| `make import` | Importa dados do StatsBomb para o banco |
| `make db-push` | Push do schema para o banco remoto |

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/tatuzinho_db` | Conexão com banco |
| `DB_POOL_SIZE` | `20` | Tamanho do pool de conexões |
| `DB_POOL_RECYCLE` | `3600` | Reciclagem de conexões (s) |
| `DEBUG` | `False` | Modo debug |
| `ENV` | `development` | Ambiente (development/production) |
| `LOG_LEVEL` | `INFO` | Nível de log |
| `SCRAPER_ENABLED` | `True` | Habilitar scraping |
| `BACKFILL_ENABLED` | `False` | Habilitar backfill |
| `BACKFILL_YEARS` | `2` | Anos de backfill |
| `PREDICTION_MODEL_PATH` | `/tmp/prediction_model.pkl` | Caminho do modelo |
| `MIN_HISTORICAL_MATCHES` | `5` | Mínimo de partidas para confiança |

## Endpoints da API

### Torneios

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/tournaments/` | Lista torneios |
| GET | `/api/v1/tournaments/{id}` | Detalhes do torneio |
| GET | `/api/v1/tournaments/{id}/standings` | Classificação do torneio |

### Partidas

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/matches/` | Lista partidas (filtros: tournament_id, phase, group, status) |
| GET | `/api/v1/matches/{id}` | Detalhes da partida |
| GET | `/api/v1/matches/{id}/statistics` | Estatísticas da partida |

### Times

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/teams/` | Lista times |
| GET | `/api/v1/teams/{id}` | Time com jogadores |
| GET | `/api/v1/teams/{id}/analytics` | Analytics do time (forma recente, aproveitamento) |
| GET | `/api/v1/teams/{id}/recent-matches` | Partidas recentes do time |

### Analytics

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/analytics/top-scorers` | Artilheiros de um torneio |
| GET | `/api/v1/analytics/top-assistants` | Assistências de um torneio |
| GET | `/api/v1/analytics/tournaments/{id}/summary` | Resumo do torneio |
| GET | `/api/v1/analytics/comparison/{team1}/{team2}` | Comparação head-to-head entre dois times |

### Predições

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/predictions/predict` | Predição do resultado de uma partida |

## Modelo de Predição (Poisson)

O endpoint `/api/v1/predictions/predict` aceita dois times (por ID ou nome) e retorna as probabilidades de vitória do mandante, empate e vitória do visitante.

**Exemplo:**
```
GET /api/v1/predictions/predict?home_team=Brazil&away_team=Argentina
```

```json
{
  "home_team": "Brazil",
  "away_team": "Argentina",
  "home_win_probability": 45.2,
  "draw_probability": 28.5,
  "away_win_probability": 26.3,
  "most_likely_score": "1-0",
  "predicted_home_goals": 1.35,
  "predicted_away_goals": 0.89,
  "confidence": 95.0
}
```

### Como funciona

1. **Médias da liga**: calcula a média de gols em casa e fora de todas as partidas no banco
2. **Força dos times**: para cada time, calcula a média de gols marcados (ataque) e sofridos (defesa) em partidas como mandante/visitante
3. **Razões**: compara a força de cada time com a média da liga
4. **Gols esperados (λ)**: ajusta as médias pela força de ataque do time e fragilidade da defesa adversária
5. **Poisson**: para cada placar possível (0x0 a 6x6), calcula `P(k) = (λ^k × e^(-λ)) / k!` e acumula as probabilidades de vitória/empate/derrota
6. **Confiança**: baseada na quantidade de partidas históricas disponíveis para ambos os times

O modelo segue a abordagem clássica de **Maher (1982) / Dixon-Coles (1997)**, assumindo que os gols de cada time seguem uma distribuição de Poisson independente.

## Estrutura do Projeto

```
tatuzinho/
├── app/
│   ├── main.py                        # FastAPI app, exception handlers
│   ├── config.py                      # Configuração + logging JSON
│   ├── database.py                    # SQLAlchemy engine/session
│   ├── models.py                      # ORM: Tournament, Team, Player, Match...
│   ├── schemas.py                     # Pydantic schemas
│   ├── exceptions.py                  # Exceções customizadas
│   ├── cache.py                       # CacheManager (Redis)
│   ├── statsbomb_importer.py          # Importador de dados StatsBomb
│   ├── routers/
│   │   ├── tournaments.py
│   │   ├── matches.py
│   │   ├── teams.py
│   │   ├── analytics.py
│   │   └── predictions.py
│   ├── services/
│   │   ├── __init__.py                # BaseService
│   │   ├── tournament_service.py
│   │   ├── match_service.py
│   │   ├── team_service.py
│   │   ├── player_service.py
│   │   ├── analytics_service.py
│   │   └── prediction_service.py
│   └── repositories/
│       ├── __init__.py                # BaseRepository
│       ├── tournament.py
│       ├── match.py
│       ├── team.py
│       └── player.py
├── docker-compose.yml                 # PostgreSQL + Redis
├── requirements.txt
├── Makefile
└── .env.example
```

## Fonte de Dados

Os dados históricos são importados do [StatsBomb Open Data](https://github.com/statsbomb/open-data), que inclui:

- Copas do Mundo (2010, 2014, 2018, 2022)
- Euro (2016, 2020)
- Copa América (2015, 2016, 2021)
- Copa Africana de Nações (2017, 2021)
- E outros torneios

Execute `make import` para popular o banco com os dados disponíveis.

## Licença

MIT
