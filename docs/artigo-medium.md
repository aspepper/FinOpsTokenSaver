# Sobrevivendo ao Caos e aos Custos das APIs de IA (Sem Entrar em Pânico)

Como estou desenhando o FinOpsTokenSaver, um AI Gateway open-source focado em resiliência e economia, pensado para rodar de forma leve em infraestrutura gratuita.

Se você já integrou algum modelo de linguagem (LLM) em um sistema real, provavelmente já passou por duas fases distintas.

A primeira é o encantamento: a IA responde bem, o sistema parece mágico e tudo flui.

A segunda fase, que costuma chegar sem aviso, é o choque de realidade.

Ele aparece na forma de uma fatura alta no fim do mês por causa de tokens desperdiçados em perguntas repetidas. Ou, pior, na forma de erros `429 Too Many Requests` derrubando a experiência do usuário porque o provedor limitou sua taxa de chamadas.

Quando isso acontece, a reação inicial de muitos times é entrar em pânico, aumentar limites do cartão corporativo ou espalhar `try/catch` mal resolvido por toda a aplicação.

Mas esse problema não deveria ficar espalhado pelo código de produto. Com um pouco de engenharia de software e foco em arquitetura, dá para tratar custo, cache, retry e auditoria em uma camada centralizada.

Foi exatamente por isso que comecei o FinOpsTokenSaver.

## O que é o FinOpsTokenSaver?

O FinOpsTokenSaver é um AI Gateway open-source em fase de MVP. A ideia é atuar como um proxy reverso entre a aplicação cliente e uma API de IA.

Em vez de cada serviço da empresa implementar sua própria lógica de cache, retry e métrica financeira, o gateway centraliza essas responsabilidades.

O objetivo é duplo:

1. **Otimização Financeira (FinOps):** reduzir chamadas repetidas para provedores pagos.
2. **Resiliência Arquitetural:** proteger a aplicação contra falhas transitórias, timeouts e rate limits.

Também impus uma restrição de design ao projeto: manter a arquitetura pequena o suficiente para funcionar em cenários de estudo, demo, protótipo e cargas leves usando serviços gratuitos ou com free tier, como Azure App Service F1, Redis Free Tier e Neon Serverless Postgres.

Essa não é uma promessa de produção sem custo. Free tiers têm limites importantes. A proposta é mostrar que uma arquitetura bem desenhada pode começar simples, barata e evoluir sem virar um acoplamento difícil de manter.

## Como funciona debaixo do capô?

O projeto foi organizado em camadas de domínio, aplicação, infraestrutura e API. A implementação atual já possui autenticação, cache exato, política de retry, cálculo de métricas FinOps, adaptadores Redis/Postgres e smoke tests locais.

O fluxo esperado de uma requisição é este:

1. A aplicação cliente envia um `POST /v1/chat/completions` para o gateway.
2. O gateway valida a API key interna.
3. O payload relevante é transformado em uma representação canônica.
4. Uma chave SHA-256 é gerada a partir dessa representação.
5. Se houver cache configurado e a chave existir, a resposta cacheada é devolvida.
6. Se não houver cache hit, o payload segue para o provedor configurado.
7. Ao final, métricas de custo, tokens, economia estimada e latência podem ser gravadas de forma assíncrona.

## 1. O Cache de Sobrevivência

O primeiro ponto de economia é simples: não pagar duas vezes pela mesma resposta.

Quando uma requisição chega ao gateway, o sistema não gera um hash apenas do texto do prompt. Ele gera uma chave determinística baseada no payload canônico da chamada, incluindo campos como `provider`, `model`, `messages`, `temperature`, `top_p`, `max_tokens`, `response_format`, `tools` e `tool_choice`.

Isso evita um erro comum: cachear respostas iguais para requisições que parecem parecidas, mas têm parâmetros de geração diferentes.

No MVP atual, o cache implementado é exato. Cache semântico com embeddings ainda está no roadmap pós-MVP.

## 2. Tratando instabilidade sem espalhar retry pela aplicação

Outro problema recorrente em integrações com LLMs é tratar falhas transitórias.

O projeto já possui uma política de `Exponential Backoff` com `Jitter` para erros elegíveis, como HTTP 408, 429 e 5xx. A ideia é simples: quando o provedor falha temporariamente, o gateway espera por um intervalo progressivo com aleatoriedade e tenta novamente.

Isso evita que cada aplicação cliente precise reinventar sua própria lógica de retry.

Um detalhe importante: retry não é mágica. Dependendo do backoff configurado, o usuário pode esperar alguns segundos a mais em uma falha transitória. Isso é melhor do que falhar imediatamente em muitos cenários, mas precisa ser configurado com cuidado para não estourar timeouts da aplicação.

## 3. Auditoria assíncrona para provar valor

FinOps não é apenas reduzir custo. É conseguir demonstrar a economia gerada.

Por isso, o projeto já possui uma entidade de métrica FinOps que calcula:

- tokens de prompt;
- tokens de completion;
- custo estimado;
- economia estimada em cache hit;
- latência;
- modelo usado;
- versão da tabela de preços;
- status do cache.

A persistência pode ser feita em Postgres por meio de um repositório assíncrono. A gravação roda em background task para não bloquear a resposta HTTP principal.

Com isso, o gateway cria a base para dashboards futuros capazes de responder perguntas como:

> Quanto economizamos este mês evitando chamadas repetidas ao provedor?

## O que já está pronto no MVP?

Hoje o projeto já tem:

- endpoint `POST /v1/chat/completions`;
- autenticação por API key interna;
- health check;
- payload canônico para cache;
- cache exato;
- adaptador Redis;
- política de retry com backoff e jitter;
- cálculo de custo estimado;
- cálculo de economia estimada;
- persistência assíncrona de métricas em Postgres;
- migração SQL inicial;
- headers de observabilidade;
- smoke test local;
- Dockerfile para execução em container.

## O que ainda falta?

Para o gateway ficar totalmente alinhado com a visão final, os próximos passos são:

- implementar o adaptador real para OpenAI;
- conectar automaticamente OpenAI, Redis e Postgres no bootstrap padrão da aplicação;
- envolver o provider real com a política de retry;
- retornar o número real de tentativas no header `X-Retry-Count`;
- adicionar smoke tests opcionais com Redis e Postgres reais;
- medir cache hit com Redis real antes de publicar números de latência;
- evoluir suporte a Anthropic e Gemini;
- implementar cache semântico com embeddings;
- criar dashboard de métricas FinOps.

## Conclusão: engenharia é sobre resolver problemas reais

Integrar IA não é apenas fazer chamadas HTTP para um modelo. É gerenciar custo, estabilidade, observabilidade e evolução dessa integração ao longo do tempo.

O FinOpsTokenSaver nasceu desse incômodo: como criar uma camada pequena, testável e extensível para proteger aplicações que dependem de LLMs?

O código completo, o Documento de Requisitos Técnicos, o roadmap e as tarefas de engenharia estão abertos no GitHub.

Repositório: https://github.com/aspepper/FinOpsTokenSaver

Convido você a testar, abrir issues, criticar a arquitetura ou contribuir com pull requests. A ideia é evoluir o projeto com a comunidade, sem vender free tier como bala de prata e sem esconder as partes que ainda estão em construção.

## Apoie o Projeto

O FinOpsTokenSaver é um projeto open-source mantido com dedicação para ajudar a comunidade a estudar FinOps aplicado a IA e construir arquiteturas mais resilientes.

Se este software ajudou você nos estudos ou inspirou alguma solução na sua empresa, considere apoiar o desenvolvimento contínuo.

PIX (Brasil): `d3ad72f7-17c0-4a3d-b286-63ceaedc7dc9`
