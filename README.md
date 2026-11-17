# GO Quest Finder

Aplicativo web progressivo (PWA), gratuito e em português, para pesquisar missões de pesquisa de campo do Pokémon GO publicadas por fontes comunitárias públicas.

## Publicar gratuitamente com GitHub Pages
1. Abra **Settings → Pages** neste repositório.
2. Em **Build and deployment**, selecione **Deploy from a branch**.
3. Escolha a branch **main** e a pasta **/(root)** e salve.
4. Aguarde o GitHub publicar e abra o endereço exibido nessa tela.

## Coleta automática
O workflow `.github/workflows/collect-quests.yml` executa diariamente às **05:23 no horário de Mato Grosso do Sul (UTC-4)** e também pode ser iniciado manualmente em **Actions → Coleta automática de Field Research → Run workflow**.

A coleta possui duas trilhas independentes:

- **Busca mundial geral:** consultas públicas amplas em Google News RSS e Reddit RSS.
- **Missões específicas:** cada objeto de `config/searches.json` gera consultas próprias, separadas das consultas gerais. O exemplo inicial procura “Make an Excellent Throw” associada a 25 doces de Eternatus.

Para adicionar uma missão específica, edite `config/searches.json` e acrescente um objeto em `specific_searches`, com `id`, `name`, `task_terms`, `reward_terms` e `search_queries`.

## Critério de inclusão e limites
- O coletor só grava uma entrada quando encontra missão, recompensa e um par de coordenadas válidas associados no conteúdo público consultado.
- Não inventa coordenadas nem recompensas e não tenta acessar conteúdo com login, assinatura ou paywall.
- Registros são deduplicados por missão + recompensa + coordenadas.
- O arquivo `data/collection-status.json` informa a última execução e quantos registros novos foram aceitos.
- A etiqueta “associadas à fonte” significa que os três dados apareceram juntos no conteúdo público; **não substitui a confirmação dentro do Pokémon GO**.
- A busca usa fontes públicas e cobertura parcial. Não existe API pública oficial do Pokémon GO para consultar todas as pesquisas de campo de todas as PokéStops; portanto, o projeto nunca declara cobertura mundial completa.

## Dados
A base `data/quests.json` começa vazia de propósito. O coletor atualiza esse arquivo automaticamente quando encontra registros que passam pelos critérios acima. Coordenadas sem associação clara à missão e à recompensa são descartadas.

## Privacidade e segurança
Não coloque tokens, senhas ou credenciais no código. O workflow usa apenas permissões de escrita do próprio GitHub Actions no repositório.
