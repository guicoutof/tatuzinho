# Analysis Framework

Use este formato quando o usuario pedir uma analise completa ou quando o jogo tiver informacoes recentes suficientes para justificar mais detalhe.

## Estrutura Recomendada

1. **Resumo**
   - Jogo, competicao, data do jogo se conhecida e timestamp da analise.
   - Leitura curta: favorito, placar provavel ou risco principal.

2. **Baseline Tatuzinho**
   - Probabilidades de vitoria/empate/derrota.
   - Gols esperados, over 2.5, placar mais provavel e confianca.
   - Forma recente de cada time, gols pro/contra, aproveitamento e H2H.
   - Jogadores listados no elenco local que ajudam a orientar buscas web.

3. **Contexto Atual**
   - Noticias confirmadas sobre lesoes, suspensoes, convocacoes, tecnico, calendario, viagem e provavel escalao.
   - Momento recente em jogos oficiais mais atuais, se a web trouxer dados que o banco historico nao cobre.
   - Fontes com publisher, data e link.

4. **Ajuste Sobre o Modelo**
   - Diga o que reforca o baseline do Tatuzinho.
   - Diga o que reduz a confianca do baseline.
   - Separe claramente dado local, fato web e inferencia.

5. **Conclusao**
   - Lean final: mandante, empate ou visitante.
   - Nivel de confianca qualitativo: baixo, medio ou alto.
   - Principais riscos para o palpite.

## Regras

- Use datas absolutas em fatos temporais.
- Cite links para noticias e fontes externas.
- Nao fabrique lesoes, odds, escalao ou estatisticas que nao aparecam nas fontes.
- Quando fontes conflitarem, mostre o conflito e reduza a confianca.
- Em jogos futuros, prefira "provavel" e "tende a" em vez de certeza.
