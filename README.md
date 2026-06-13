# Tatuzinho - Football Analytics API

API de análise de partidas de futebol com previsão de resultados usando modelo estatístico **Poisson**. Alimentada por dados históricos do [StatsBomb Open Data](https://github.com/statsbomb/open-data).

## Stack

- **Python 3.11+** / **FastAPI**
- **PostgreSQL** via Docker local ou banco externo compatível
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
- Python 3.11+
- Make

## Instalação

```bash
# 1. Clone e entre no diretório
git clone <repo> && cd tatuzinho

# 2. Configure as variáveis de ambiente para Docker local
cp .env.example .env
# Para Supabase/PostgreSQL externo, troque DATABASE_URL no .env

# 3. Instale dependências Python
make install-deps

# 4. Inicie os serviços Docker locais (PostgreSQL + Redis)
make up

# 5. Inicie o servidor de desenvolvimento
make start-dev
```

Acesse a documentação interativa em http://localhost:8000/docs

### Importação de Dados

Depois que o banco estiver ativo, importe a base StatsBomb e recalcule os dados derivados:

```bash
make import
make db-maintenance
```

O importador lê lineups e eventos de partidas para preencher aparições, minutos estimados, gols, assistências e cartões por jogador. Ao final da importação, a rotina de manutenção sincroniza `tournament_teams` e recalcula estatísticas agregadas de times e jogadores.

Se estiver usando um banco externo, defina `DATABASE_URL` antes dos comandos:

```bash
DATABASE_URL=postgresql://user:password@host:5432/database make import
DATABASE_URL=postgresql://user:password@host:5432/database make db-maintenance
```

## Comandos

| Comando | Descrição |
|---|---|
| `make dev` | Sobe containers + servidor dev (reload automático) |
| `make prod` | Servidor produção |
| `make up` | Sobe containers Docker (PostgreSQL + Redis) |
| `make down` | Para containers Docker |
| `make install-deps` | Instala dependências Python |
| `make import` | Importa dados do StatsBomb para o banco |
| `make db-maintenance` | Sincroniza relações e recalcula estatísticas derivadas |
| `make db-push` | Push do schema para o banco remoto |

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/tatuzinho_dev` | Conexão com banco |
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
| `OPENAI_API_KEY` | vazio | Chave opcional para análise de partidas com IA |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Base URL compatível com OpenAI Responses API |
| `AI_ANALYSIS_MODEL` | `gpt-4.1-mini` | Modelo usado pelo serviço de análise com IA |
| `AI_WEB_SEARCH_ENABLED` | `True` | Permite busca web quando a análise com IA estiver ativa |
| `AI_ANALYSIS_TIMEOUT_SECONDS` | `45` | Timeout da chamada de análise com IA |

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

O endpoint `/api/v1/predictions/predict` aceita dois times (por ID, nome ou código) e retorna as probabilidades de vitória do primeiro time, empate e vitória do segundo time. O modelo trata jogos internacionais como campo neutro, sem vantagem fixa de mando.

**Exemplo:**
```
GET /api/v1/predictions/predict?home_team=Brazil&away_team=Argentina
```

```json
{
  "home_team": "Brazil",
  "away_team": "Argentina",
  "home_team_id": 1,
  "away_team_id": 2,
  "home_win_probability": 45.2,
  "draw_probability": 28.5,
  "away_win_probability": 26.3,
  "over_25_probability": 48.7,
  "most_likely_score": "1-0",
  "predicted_home_goals": 1.35,
  "predicted_away_goals": 0.89,
  "confidence": 95.0
}
```

### Como funciona

1. **Média global**: calcula gols por time por partida usando todas as partidas finalizadas, com peso maior para jogos recentes
2. **Referência temporal**: usa a data da partida mais recente no banco como âncora de recência, evitando perda artificial de peso em datasets históricos
3. **Força dos times**: para cada time, calcula gols marcados (ataque) e sofridos (defesa) com ponderação exponencial por recência
4. **Estabilização**: ajusta ataque e defesa em direção à média global quando há poucas partidas efetivas, reduzindo previsões extremas por amostra pequena
5. **Forma recente**: aplica um ajuste pequeno com base em pontos ponderados e saldo de gols recente
6. **Qualidade do elenco**: usa gols e assistências importados dos eventos StatsBomb para ajustar a força ofensiva
7. **Confronto direto**: aplica uma correção limitada por amostra para histórico entre os dois times
8. **Gols esperados (λ)**: combina ataque do time, fragilidade defensiva do adversário e os modificadores acima, limitando valores extremos
9. **Poisson**: calcula os placares de 0x0 a 10x10, acumula vitória/empate/derrota e normaliza a massa de probabilidade
10. **Over 2.5**: calcula a probabilidade de mais de 2.5 gols diretamente pela distribuição de gols totais, sem depender do limite da grade de placares
11. **Confiança**: combina volume equilibrado de partidas, profundidade de dados de elenco e amostra de forma recente

O modelo segue a abordagem clássica de **Maher (1982) / Dixon-Coles (1997)**, assumindo que os gols de cada time seguem uma distribuição de Poisson independente.

## Análise de Partidas com IA

`app/services/ai_analysis_service.py` combina a predição local, analytics dos times, partidas recentes, confronto direto e principais jogadores com uma chamada opcional à OpenAI Responses API. Sem `OPENAI_API_KEY`, o serviço retorna uma análise local de fallback e informa que o enriquecimento por IA está desativado.

Para habilitar:

```bash
OPENAI_API_KEY=sk-... make start-dev
```

Quando `AI_WEB_SEARCH_ENABLED=True`, o serviço permite busca web para complementar a análise com notícias recentes de escalações, lesões, suspensões e contexto competitivo. Esses dados devem ser tratados como complemento ao histórico local, não como garantia de resultado.

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
│   ├── db_maintenance.py              # Rotinas de manutenção derivada do banco
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
│   │   ├── ai_analysis_service.py
│   │   └── prediction_service.py
│   └── repositories/
│       ├── __init__.py                # BaseRepository
│       ├── tournament.py
│       ├── match.py
│       ├── team.py
│       └── player.py
├── docker-compose.yml                 # PostgreSQL + Redis
├── skills/                            # Skills locais para agentes de análise
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

Execute `make import` para popular o banco com os dados disponíveis. Se você já tem dados importados e quer apenas recalcular relações e estatísticas derivadas, execute `make db-maintenance`.

## Licença

MIT
