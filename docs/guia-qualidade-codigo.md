# Guia de Qualidade de Codigo

Este guia traduz SOLID, Clean Code, Design Patterns e Object Calisthenics para decisoes praticas no FinOpsTokenSaver.

---

## Principios de Arquitetura

* O dominio nao deve importar framework HTTP, Redis, Postgres ou SDK de provedor.
* Casos de uso orquestram dependencias, mas nao devem conter detalhes de infraestrutura.
* Adaptadores ficam nas bordas e implementam contratos definidos pela aplicacao.
* Regras de cache, retry, autenticacao e precificacao devem ser testaveis sem rede.
* Otimizacoes para camada gratuita devem ser medidas e documentadas, nao espalhadas como atalhos no codigo.

---

## SOLID no Projeto

### Single Responsibility
Cada componente deve ter apenas um motivo claro para mudar.

**Exemplos:**
* `GatewayAuthenticator` muda por regra de autenticacao.
* `CacheKeyFactory` muda por regra de canonicalizacao.
* `OpenAIProviderClient` muda por contrato da OpenAI.
* `FinOpsMetricRepository` muda por persistencia.

### Open/Closed
Novos provedores devem entrar por novos adapters.

**Evitar:** `if provider == "openai"` espalhado no fluxo principal.

**Preferir:** factory ou registry que resolve uma implementacao de `ProviderClient`.

### Liskov Substitution
Qualquer `ProviderClient` deve poder substituir outro sem quebrar o caso de uso.

**Regra:** contratos de erro, timeout, token usage e corpo de resposta devem ser consistentes.

### Interface Segregation
Criar interfaces pequenas e orientadas a uso.

**Boas interfaces iniciais:**
* `ProviderClient`
* `CacheStore`
* `MetricsRepository`
* `PricingCatalog`
* `RetryPolicy`
* `Clock`

### Dependency Inversion
Casos de uso recebem dependencias por construtor ou mecanismo equivalente.

**Regra:** codigo de aplicacao depende de abstracoes; infraestrutura depende dessas abstracoes para implementar detalhes.

---

## Clean Code no Projeto

### Nomes
Use nomes que carreguem contexto de negocio.

**Preferir:**
* `calculate_saved_cost`
* `is_cacheable_response`
* `build_canonical_payload`
* `record_finops_metric`

**Evitar:**
* `handle_data`
* `process`
* `do_request`
* `calc`

### Funcoes
* Uma funcao deve executar uma acao clara.
* Parametros demais indicam que talvez falte um objeto de valor.
* Retornos devem ser previsiveis; evite misturar `null`, excecao e objeto de erro para o mesmo caso.

### Erros
* Erros esperados devem ter tipos explicitos.
* Mensagens publicas nao devem expor detalhes internos.
* Logs internos podem ter contexto tecnico, mas sem segredo nem prompt completo.

### Configuracao
* Nao espalhar acesso a variaveis de ambiente.
* Defaults devem ser visiveis e justificados.
* Configuracao obrigatoria deve falhar no startup.

---

## Design Patterns Recomendados

### Adapter
Use para provedores externos.

**Onde aplicar:** `OpenAIProviderClient`, `AnthropicProviderClient`, `GeminiProviderClient`.

### Strategy
Use para regras variaveis.

**Onde aplicar:** retry, cacheabilidade, precificacao e escolha de provedor.

### Repository
Use para persistencia de metricas.

**Onde aplicar:** `PostgresMetricsRepository`.

### Decorator
Use para adicionar comportamento sem poluir o adapter.

**Onde aplicar:** `RetryingProviderClient`, `LoggingProviderClient`, `MetricsProviderClient`.

### Factory
Use para montar dependencias conforme configuracao.

**Onde aplicar:** criacao de clients de provedor, Redis e repositorio de metricas.

---

## Object Calisthenics Aplicado

### Uma Responsabilidade por Classe
Se uma classe autentica, chama provedor, calcula preco e salva metrica, ela deve ser quebrada.

### Encapsular Primitivos com Significado
Use objetos de valor quando a regra importar.

**Candidatos:**
* `RequestId`
* `CacheKey`
* `TokenUsage`
* `Money`
* `Latency`
* `ProviderName`

### Evitar Encadeamento Profundo
**Evitar:** acessar estruturas aninhadas repetidamente.

**Preferir:** criar metodos de intencao como `response.token_usage()` ou `payload.model_name()`.

### Encapsular Colecoes
Se a colecao tem regra, ela merece tipo proprio.

**Exemplo:** `ChatMessages` pode validar formato, canonicalizar conteudo e esconder detalhes do array bruto.

### Reduzir `else`
Use retornos antecipados em validacoes simples.

```text
se nao autenticado, retornar 401
se bypass de cache, chamar provedor
se cache hit, retornar resposta cacheada
chamar provedor e salvar resultado
```

### Classes Pequenas
Como referencia inicial, uma classe com mais de uma responsabilidade ou muitos metodos publicos deve ser revisada.

---

## Checklist de Revisao para o Codex

Antes de concluir uma tarefa, verificar:

* A mudanca atende exatamente a tarefa solicitada.
* Regras de negocio novas possuem teste.
* Controller continua fino.
* Nenhum segredo ou prompt completo foi adicionado a logs.
* Nao ha dependencia de infraestrutura dentro do dominio.
* Nomes expressam intencao.
* Erros esperados possuem tratamento claro.
* Testes nao dependem de tempo real quando houver retry/backoff.
* Configuracoes novas estao documentadas.
* A execucao local continua simples.

---

## Sinais de Problema

Revise a implementacao quando aparecer:

* `if` por provedor espalhado em varios arquivos.
* Funcoes chamadas `process`, `handle` ou `manager` sem contexto claro.
* Testes que precisam de OpenAI, Redis ou Postgres para validar regra pura.
* Logs contendo payload completo.
* Calculo financeiro com ponto flutuante binario.
* Retry que usa `sleep` real em teste.
* Controller HTTP com regra de cache, retry ou precificacao.
