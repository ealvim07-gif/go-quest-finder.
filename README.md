# GO Quest Finder

Aplicativo web progressivo (PWA) em português para pesquisar missões comunitárias de Pokémon GO.

## Publicar gratuitamente com GitHub Pages
1. Abra **Settings → Pages** neste repositório.
2. Em **Build and deployment**, selecione **Deploy from a branch**.
3. Escolha a branch **main** e a pasta **/(root)** e salve.
4. Aguarde o GitHub publicar e abra o endereço exibido nessa tela.

## Dados
A base inicial `data/quests.json` está vazia de propósito. Não inventamos missões ou coordenadas. Para adicionar um registro, use este formato:

```json
[
  {
    "task": "Faça uma jogada excelente",
    "reward": "Recompensa confirmada",
    "type": "Pesquisa de campo",
    "city": "Cidade",
    "country": "País",
    "lat": -23.0,
    "lng": -46.0,
    "verified": true,
    "source": "https://exemplo.com/fonte",
    "updated_at": "2026-11-17"
  }
]
```

Use `verified: true` somente após conferir a localização e a missão. Coordenadas não verificadas não aparecem no mapa.

## Limitações atuais
Esta versão já tem interface de pesquisa, filtros e mapa, mas **ainda não coleta missões automaticamente**. O Pokémon GO não oferece uma API pública oficial para consultar todas as pesquisas de campo do mundo. A coleta automática exigirá fontes públicas acessíveis, regras de uso compatíveis e um processo agendado (por exemplo, GitHub Actions). Não compartilhe credenciais ou tokens no código.
