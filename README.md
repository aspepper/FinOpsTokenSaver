# FinOpsTokenSaver 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Azure](https://img.shields.io/badge/Hosted_on-Azure_App_Service-0089D6?logo=microsoft-azure)](https://azure.microsoft.com/)
[![Redis](https://img.shields.io/badge/Cache-Redis_Free_Tier-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Neon](https://img.shields.io/badge/Database-Neon_Postgres-00E599?logo=postgresql&logoColor=black)](https://neon.tech/)

O **FinOpsTokenSaver** é um gateway de IA e proxy reverso inteligente, projetado para reduzir custos de tokens e aumentar a resiliência de aplicações que utilizam LLMs.

O projeto está em fase de MVP funcional. A base arquitetural cobre autenticação, proxy para OpenAI, cache exato com Redis, retry com backoff e jitter, métricas FinOps, persistência assíncrona em Postgres/Neon, smoke tests opcionais com infraestrutura real e empacotamento em container.

Toda a arquitetura foi desenhada de forma leve para rodar em cenários de estudo, demo, protótipo e cargas pequenas dentro dos limites de **infraestrutura 100% gratuita** (Azure Free F1, Neon Serverless e Redis Free Tier).

---

## 💡 Por que o FinOpsTokenSaver?

Integrar inteligência artificial em sistemas corporativos traz dois grandes problemas: **custos imprevisíveis de tokens** e **erros de Rate Limiting (HTTP 429)**. O FinOpsTokenSaver atua como um intermediário inteligente para resolver ambos:

*   **Cache Exato (FinOps):** Reaproveita respostas de requisições idênticas, usando uma chave determinística baseada no payload canônico.
*   **Resiliência:** Implementa uma política de *Exponential Backoff com Jitter* para falhas transitórias, como HTTP 408, 429 e 5xx.
*   **Auditoria Assíncrona de Custos:** Calcula custo estimado, economia estimada, tokens e latência, com persistência assíncrona em Postgres/Neon quando `DATABASE_URL` está configurado.

---

## 🛠️ Arquitetura do Sistema

O fluxo de dados foi projetado para respeitar os limites de memória da camada gratuita da Azure (1GB RAM compartilhado):

1. **Cliente** envia a requisição para o endpoint `POST /v1/chat/completions`.
2. O Gateway valida a API key interna.
3. Quando `REDIS_URL` está configurado, o Gateway gera uma chave canônica e consulta o Redis.
4. Em *Cache Hit*, a resposta cacheada é devolvida sem acionar o provedor.
5. Em *Cache Miss*, o Gateway encaminha o payload para a OpenAI quando `OPENAI_API_KEY` está configurada.
6. A chamada ao provedor é envolvida por `RetryingProviderClient`, com retry para HTTP 408, 429 e 5xx.
7. Quando `DATABASE_URL` está configurado, uma background task registra métricas financeiras e operacionais em Postgres/Neon.

---

## 📌 Estado Atual do MVP

### Implementado

* Rota `POST /v1/chat/completions` compatível com o formato de Chat Completions.
* Autenticação via `Authorization: Bearer <gateway_api_key>`.
* Provider real para OpenAI (`OpenAIProviderClient`) usando `OPENAI_API_KEY`.
* Bootstrap por configuração para montar OpenAI, Redis e Postgres/Neon automaticamente.
* Retry com exponential backoff e jitter para HTTP 408, 429 e 5xx.
* Header `X-Retry-Count` com a contagem real de retries executados.
* Geração de `X-Request-Id`, `X-Cache-Status`, `X-Provider` e `X-Gateway-Latency-Ms`.
* Cache exato baseado em payload canônico.
* Adaptador Redis (`RedisCacheStore`) com TTL e prefixo opcional.
* Política de cacheabilidade para evitar cache de streaming, bypass e erros.
* Entidade de métrica FinOps com custo estimado e economia estimada.
* Repositório Postgres assíncrono para métricas.
* Migração inicial da tabela `tb_finops_metrics`.
* Smoke test local com provedor fake e cache em memória.
* Smoke test opcional com Redis real quando `REDIS_URL` está configurado.
* Smoke test opcional com Postgres/Neon real quando `DATABASE_URL` está configurado.
* Benchmark opcional de cache hit com Redis real.
* Dockerfile e documentação para execução em container.

### Pós-MVP

* Suporte a Anthropic e Gemini via novos adapters.
* Cache semântico com embeddings.
* Dashboard de métricas FinOps.
* Rate limiting por chave de cliente.
* Multi-tenant.
* Fallback automático entre provedores.

---

## 🚀 Como Executar Localmente

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m uvicorn finops_token_saver.main:app --reload
```

Em outro terminal, execute os testes:

```bash
make test
```

Smoke test do fluxo principal:

```bash
make smoke
```

O smoke test sobe a aplicação localmente em loopback com provedor e cache em memória,
executa `/health`, chamada não autenticada, cache miss autenticado e cache hit
autenticado. A saída mostra status HTTP e headers principais, sem imprimir prompts
ou credenciais.

Smoke test opcional com Redis real:

```bash
REDIS_URL=redis://localhost:6379/0 make smoke-redis
```

Esse comando usa provedor fake local, executa duas chamadas idênticas e valida
`MISS` seguido de `HIT` usando a instância Redis configurada. Se `REDIS_URL` não
estiver definido, o teste é pulado automaticamente. As chaves criadas usam um
prefixo `finops-token-saver:integration:<uuid>:` e a limpeza remove somente
chaves desse prefixo.

Smoke test opcional com Postgres ou Neon real:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/finops_token_saver make smoke-postgres
```

Esse comando aplica a migração `migrations/001_create_finops_metrics.sql` se
necessário, executa uma chamada com provedor fake local e consulta
`tb_finops_metrics` pelo `request_id` de teste. Se `DATABASE_URL` não estiver
definido, o teste é pulado automaticamente. A limpeza remove somente a linha com
o `request_id` usado pelo smoke test.

Benchmark opcional de cache hit com Redis real:

```bash
BENCHMARK_ENVIRONMENT=local \
BENCHMARK_REQUESTS=100 \
REDIS_URL=redis://localhost:6379/0 \
make benchmark-redis
```

O benchmark usa provedor fake local, aquece o cache antes da medição e mede
somente chamadas com `X-Cache-Status: HIT`. A saída reporta `mean_ms`, `p50_ms`,
`p95_ms` e `p99_ms`, além do ambiente informado em `BENCHMARK_ENVIRONMENT`.
Use valores publicados apenas quando vierem de uma execução real nesse ambiente
específico, por exemplo `local`, `azure-container-apps + redis-free-tier` ou
outro rótulo que descreva onde o teste rodou.

### Alternativa com container

Se o deploy alvo for Azure Container Apps, a aplicação também pode ser empacotada
como imagem OCI usando o `Dockerfile` do projeto.

Build local:

```bash
docker build -t finops-token-saver:local .
```

Execução local do container:

```bash
docker run --rm -p 8000:8000 \
  -e APP_ENV=development \
  -e GATEWAY_API_KEYS=local-dev-key \
  finops-token-saver:local
```

Health check:

```bash
curl -i http://127.0.0.1:8000/health
```

Para publicar no Azure Container Apps, envie a imagem para um registry, como Azure
Container Registry, e crie ou atualize o container app apontando para essa imagem.
O container escuta a porta `8000` por default e respeita a variável `PORT` quando
ela for definida pela plataforma.

Exemplo usando uma imagem já publicada:

```bash
az containerapp up \
  --name finops-token-saver \
  --resource-group <RESOURCE_GROUP> \
  --location <AZURE_REGION> \
  --image <REGISTRY>/finops-token-saver:<TAG> \
  --ingress external \
  --target-port 8000
```

Configure segredos e variáveis obrigatórias pelo recurso do Container App, pelo
Azure CLI ou por Key Vault. Não inclua valores reais de `GATEWAY_API_KEYS`,
`OPENAI_API_KEY`, `REDIS_URL` ou `DATABASE_URL` no Dockerfile, na imagem ou no
histórico do shell.

### Configuração

Em `development`, a aplicação usa defaults locais seguros para subir sem segredos reais.
Para `staging` ou `production`, configure obrigatoriamente:

* `GATEWAY_API_KEYS`
* `OPENAI_API_KEY`
* `REDIS_URL`
* `DATABASE_URL`

Variáveis opcionais com default:

* `APP_ENV=development`
* `CACHE_TTL_SECONDS=43200`
* `PROVIDER_TIMEOUT_SECONDS=30`
* `MAX_RETRY_ATTEMPTS=3`
* `LOG_LEVEL=INFO`

### Configuração para Integrações Reais

Crie um arquivo local baseado em `.env.example` ou configure as variáveis diretamente no ambiente de deploy.

#### Gateway

`GATEWAY_API_KEYS` define uma ou mais chaves internas aceitas pelo gateway. Separe múltiplas chaves por vírgula.

```bash
APP_ENV=production
GATEWAY_API_KEYS=cliente-a-key,cliente-b-key
```

As aplicações clientes devem chamar o gateway com:

```http
Authorization: Bearer cliente-a-key
```

#### Provedor OpenAI

Para usar OpenAI como provedor real:

```bash
OPENAI_API_KEY=sk-...
PROVIDER_TIMEOUT_SECONDS=30
MAX_RETRY_ATTEMPTS=3
```

Com `OPENAI_API_KEY` configurada, o gateway encaminha chamadas `POST /v1/chat/completions` para a OpenAI usando essa credencial do ambiente. O cliente final não deve enviar a chave da OpenAI; ele envia apenas a chave interna do gateway.

Exemplo de chamada ao gateway:

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer cliente-a-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Explique FinOps para APIs de IA em uma frase."}
    ],
    "temperature": 0
  }'
```

#### Redis

Para usar Redis como cache real:

```bash
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=43200
```

Em provedores com TLS, como alguns planos gerenciados, a URL pode seguir o formato `rediss://`.

```bash
REDIS_URL=rediss://default:<PASSWORD>@<HOST>:<PORT>
```

Com `REDIS_URL` configurado, o bootstrap cria `RedisCacheStore.from_url(settings.redis_url)` automaticamente. Em `development`, se `REDIS_URL` não for alterado do default local, o cache real não é ativado para permitir execução sem infraestrutura externa.

#### Postgres ou Neon

Para usar Postgres/Neon como banco real de métricas:

```bash
DATABASE_URL=postgresql://<USER>:<PASSWORD>@<HOST>/<DATABASE>?sslmode=require
```

Antes de gravar métricas, aplique a migração:

```bash
psql "$DATABASE_URL" -f migrations/001_create_finops_metrics.sql
```

Com `DATABASE_URL` configurado, o bootstrap cria `PostgresMetricsRepository.from_database_url(settings.database_url)` automaticamente. O pool é inicializado de forma lazy na primeira gravação, evitando conexão no startup.

#### Exemplo de ambiente completo

```bash
APP_ENV=production
GATEWAY_API_KEYS=cliente-a-key
OPENAI_API_KEY=sk-...
REDIS_URL=rediss://default:<PASSWORD>@<REDIS_HOST>:<REDIS_PORT>
DATABASE_URL=postgresql://<USER>:<PASSWORD>@<NEON_HOST>/<DATABASE>?sslmode=require
CACHE_TTL_SECONDS=43200
PROVIDER_TIMEOUT_SECONDS=30
MAX_RETRY_ATTEMPTS=3
LOG_LEVEL=INFO
```

#### Execução local com variáveis reais

```bash
set -a
. ./.env
set +a
python -m uvicorn finops_token_saver.main:app --reload
```

#### Execução em container com variáveis reais

```bash
docker run --rm -p 8000:8000 \
  -e APP_ENV=production \
  -e GATEWAY_API_KEYS=cliente-a-key \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e REDIS_URL="$REDIS_URL" \
  -e DATABASE_URL="$DATABASE_URL" \
  -e CACHE_TTL_SECONDS=43200 \
  -e PROVIDER_TIMEOUT_SECONDS=30 \
  -e MAX_RETRY_ATTEMPTS=3 \
  finops-token-saver:local
```

#### Verificação esperada

A verificação ponta a ponta deve cobrir:

* primeira chamada autenticada retorna `X-Cache-Status: MISS`;
* segunda chamada idêntica retorna `X-Cache-Status: HIT`;
* `X-Retry-Count` reflete tentativas reais quando houver falha transitória;
* uma linha é gravada em `tb_finops_metrics`;
* o benchmark de cache hit reporta p50, p95, p99 e média para o ambiente testado.

---

## ☕ Apoie o Projeto

O **FinOpsTokenSaver** é um projeto open-source mantido com dedicação para ajudar a comunidade a otimizar recursos e construir arquiteturas mais resilientes. Se este software ajudou sua empresa a economizar custos em produção ou facilitou seus estudos, considere apoiar o desenvolvimento contínuo!

* **PIX (Brasil):** `d3ad72f7-17c0-4a3d-b286-63ceaedc7dc9`

---

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---
Desenvolvido por [Alex Pimenta ↗](https://www.linkedin.com/in/alexpimentadev/?locale=pt) - Vamos nos conectar no LinkedIn.
