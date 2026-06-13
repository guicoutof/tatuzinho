---
name: tatuzinho-match-research
description: Analise pre-jogo ou comparativa entre dois times usando a API local do Tatuzinho para obter previsao Poisson, forma recente, elenco/jogadores, historico e confrontos diretos, combinando esses dados com noticias e informacoes recentes da internet. Use quando o usuario informar dois times e pedir previsao, preview, analise de partida, informacoes de times ou jogadores, provaveis escalacoes, lesoes, suspensoes, momento atual ou uma leitura atualizada com fontes.
---

# Tatuzinho Match Research

## Overview

Use esta skill para produzir uma analise atualizada de futebol a partir de dois times. Trate o Tatuzinho como fonte local de dados historicos/modelo e a web como fonte de contexto atual, sempre separando fatos, inferencias e incertezas.

## Workflow

1. Extraia `home_team` e `away_team` do pedido. Capture tambem competicao, data, local, idioma e profundidade quando o usuario informar.
2. Colete primeiro o pacote local do Tatuzinho:

```bash
python skills/tatuzinho-match-research/scripts/collect_tatuzinho_context.py \
  --home "Brazil" \
  --away "Argentina" \
  --base-url "${TATUZINHO_API_URL:-http://localhost:8000}"
```

3. Se a API local estiver fora do ar, informe isso claramente. Nao invente dados do Tatuzinho; continue apenas com web se o usuario aceitar ou se o pedido permitir uma analise web-only.
4. Pesquise a web por informacoes atuais. Use busca/browse por padrao, porque noticias, lesoes, suspensoes, tecnicos, convocacoes, odds e provaveis escalacoes mudam rapidamente.
5. Cruze os dados: compare a previsao e historico do Tatuzinho com as noticias recentes. Destaque quando uma noticia atual enfraquece ou fortalece o baseline historico.
6. Entregue a analise em portugues por padrao, com links de fonte e datas absolutas para afirmacoes temporais.

## Tatuzinho Data

O script auxiliar retorna JSON compacto chamando estes endpoints quando disponiveis:

- `GET /api/v1/teams/` para resolver nomes, IDs, codigos e aliases em portugues.
- `GET /api/v1/teams/{id}` para detalhes do time e jogadores.
- `GET /api/v1/teams/{id}/analytics` para forma recente, gols, aproveitamento e posse.
- `GET /api/v1/teams/{id}/recent-matches?limit=N` para partidas recentes.
- `GET /api/v1/analytics/comparison/{home_id}/{away_id}` para confronto direto.
- `GET /api/v1/predictions/predict?home_team_id=...&away_team_id=...` para probabilidades, gols esperados, placar provavel e confianca.

Use `--raw` somente quando precisar do JSON completo sem poda. Caso contrario, priorize o resumo do script para economizar contexto.

## Web Research

Monte buscas direcionadas com os dois times, competicao e jogadores relevantes do elenco:

- `"{home_team}" "{away_team}" preview lineups injuries`
- `"{home_team}" latest team news injuries suspensions`
- `"{away_team}" latest team news injuries suspensions`
- `"{competition}" "{home_team}" "{away_team}" probable lineups`
- nomes de jogadores do pacote Tatuzinho com `injury`, `suspension`, `form`, `goals`, `convocado` ou `desfalque`.

Prefira fontes oficiais de clubes/federacoes/ligas, centros de jogo, comunicados medicos, entrevistas recentes e veiculos esportivos reconhecidos. Evite tratar posts sociais ou rumores como fato; marque-os como rumor quando forem relevantes.

## Output

Leia `references/analysis-framework.md` quando o usuario pedir uma analise completa, relatorio, justificativa detalhada ou formato reutilizavel.

Inclua por padrao:

- partida e timestamp da analise
- baseline Tatuzinho: previsao, gols esperados, placar provavel, confianca, forma recente e H2H
- contexto atual: noticias, desfalques, provaveis escalacoes, momento, jogadores-chave e riscos
- ajuste interpretativo: como as informacoes recentes mudam a leitura do modelo
- palpite/lean: mandante, empate ou visitante, com nivel de confianca e principais ressalvas
- fontes com links

Nunca apresente o palpite como garantia. Se uma informacao depender de escalao oficial, treino fechado ou dado em tempo real indisponivel, diga isso diretamente.
