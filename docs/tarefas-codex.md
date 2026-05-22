# Tarefas Pequenas para o Codex

Este documento transforma o roadmap em tarefas pequenas e verificaveis. Cada tarefa deve produzir uma mudanca limitada, com testes quando houver regra de negocio.

---

## Regras Gerais para Cada Tarefa

* Ler `docs/requisitos.md`, `docs/resumo-arquitetural.md` e `docs/roadmap.md` antes de implementar.
* Manter mudancas pequenas e focadas.
* Preferir objetos de dominio e interfaces pequenas.
* Evitar acoplar regra de negocio ao framework HTTP.
* Incluir ou atualizar testes na mesma tarefa.
* Rodar testes e formatacao antes de concluir.
* Nao registrar prompts completos, chaves ou secrets em logs.

---

## Tarefa 01: Criar Esqueleto do Backend

**Objetivo:** Criar a estrutura inicial da aplicacao.

### Passos
1. Escolher a stack conforme o README ou decisao do projeto.
2. Criar pastas para `domain`, `application`, `infrastructure` e `api`.
3. Criar ponto de entrada da aplicacao.
4. Criar comando de teste.
5. Criar primeiro teste de sanidade.
6. Crie o .gitignore para o projeto criado.

### Qualidade Esperada
* Estrutura simples e sem abstracoes prematuras.
* Nenhum codigo de provedor externo ainda.
* Teste basico executavel localmente.

---

## Tarefa 02: Configuracao da Aplicacao

**Objetivo:** Centralizar configuracoes por ambiente.

### Passos
1. Criar objeto de configuracao.
2. Mapear variaveis obrigatorias e opcionais.
3. Definir defaults seguros para desenvolvimento.
4. Falhar com mensagem clara quando faltar segredo obrigatorio.
5. Adicionar testes de configuracao.

### Qualidade Esperada
* Sem leituras espalhadas de variaveis de ambiente.
* Valores magicos devem ter nomes claros.
* Segredos nunca devem ser impressos em mensagens de erro.

---

## Tarefa 03: Health Check

**Objetivo:** Expor `GET /health`.

### Passos
1. Criar rota HTTP.
2. Retornar `status` e `service`.
3. Garantir que a rota nao dependa de Redis, Postgres ou provedor LLM.
4. Adicionar teste de contrato HTTP.

### Qualidade Esperada
* Endpoint rapido.
* Sem efeitos colaterais.
* Resposta estavel para smoke tests.

---

## Tarefa 04: Autenticacao do Gateway

**Objetivo:** Bloquear chamadas sem API key interna valida.

### Passos
1. Criar componente de validacao de credencial.
2. Aceitar `Authorization: Bearer <token>`.
3. Rejeitar chave ausente, vazia ou invalida.
4. Integrar validacao na rota protegida.
5. Testar casos autorizado e nao autorizado.

### Qualidade Esperada
* Validador isolado do framework.
* Comparacao de chave sem logs de segredo.
* Falha `401` nao deve acionar dependencias externas.

---

## Tarefa 05: Contrato de Provedor LLM

**Objetivo:** Criar abstracao para provedores externos.

### Passos
1. Definir interface `ProviderClient`.
2. Definir objeto de resposta do provedor.
3. Definir erros de provedor esperados.
4. Criar implementacao fake para testes.
5. Testar substituicao do fake no caso de uso.

### Qualidade Esperada
* Interface pequena.
* Nenhuma dependencia do SDK oficial no dominio.
* Erros devem carregar status, tipo e mensagem segura.

---

## Tarefa 06: Proxy de Chat Completion

**Objetivo:** Encaminhar `POST /v1/chat/completions` para o provedor.

### Passos
1. Criar rota com corpo compativel com OpenAI.
2. Chamar caso de uso de chat completion.
3. Encaminhar payload ao `ProviderClient`.
4. Preservar corpo de resposta do provedor.
5. Testar sucesso e erro basico.

### Qualidade Esperada
* Controller fino.
* Caso de uso orquestra dependencias.
* Resposta de erro segue contrato definido.

---

## Tarefa 07: Canonicalizacao de Payload

**Objetivo:** Gerar representacao estavel para cache.

### Passos
1. Criar objeto `CanonicalPayload`.
2. Selecionar campos que influenciam resposta.
3. Ordenar propriedades JSON de forma deterministica.
4. Gerar hash SHA-256.
5. Testar payloads equivalentes e diferentes.

### Qualidade Esperada
* Sem concatenacao manual fragil.
* Testes cobrem ordem de propriedades e parametros de geracao.
* Hash nao deve expor conteudo do prompt.

---

## Tarefa 08: Politica de Cacheabilidade

**Objetivo:** Decidir quando consultar e salvar cache.

### Passos
1. Criar `CachePolicy`.
2. Bloquear cache para `stream=true`.
3. Bloquear cache para header `X-Cache-Bypass: true`.
4. Bloquear persistencia de erros.
5. Testar decisoes principais.

### Qualidade Esperada
* Regras isoladas.
* Nomes de metodos expressam intencao.
* Sem `if` duplicado em controllers.

---

## Tarefa 09: Contrato e Fake de Cache

**Objetivo:** Definir abstracao de cache antes do Redis real.

### Passos
1. Criar interface `CacheStore`.
2. Criar implementacao em memoria para testes.
3. Integrar cache no caso de uso.
4. Retornar `X-Cache-Status`.
5. Testar cache miss seguido de cache hit.

### Qualidade Esperada
* Caso de uso depende da abstracao.
* Cache hit nao chama provedor.
* TTL pode ser configurado pela implementacao.

---

## Tarefa 10: Adaptador Redis

**Objetivo:** Persistir cache em Redis.

### Passos
1. Criar implementacao `RedisCacheStore`.
2. Configurar TTL obrigatorio.
3. Tratar indisponibilidade do Redis como cache miss.
4. Limitar tamanho maximo do item cacheado.
5. Adicionar testes com mock ou container local quando disponivel.

### Qualidade Esperada
* Falha do Redis nao derruba a chamada principal.
* Serializacao preserva resposta original.
* Logs registram apenas status e request id.

---

## Tarefa 11: Retry com Backoff e Jitter

**Objetivo:** Tornar chamadas ao provedor resilientes.

### Passos
1. Criar `RetryPolicy`.
2. Definir erros elegiveis para retry.
3. Implementar calculo de atraso com jitter.
4. Integrar no caso de uso ou decorator do provider.
5. Testar sucesso apos retry e falha final.

### Qualidade Esperada
* 4xx de cliente nao devem ser retentados.
* Numero maximo de tentativas configuravel.
* Testes nao devem dormir de verdade; usar relogio ou sleeper fake.

---

## Tarefa 12: Catalogo de Precos

**Objetivo:** Calcular custo estimado por modelo.

### Passos
1. Criar objeto `TokenUsage`.
2. Criar objeto `Money` ou valor decimal equivalente.
3. Criar `PricingCatalog`.
4. Adicionar precos iniciais configuraveis.
5. Testar calculo de prompt, completion e total.

### Qualidade Esperada
* Usar decimal para valores financeiros.
* Modelo desconhecido nao falha a requisicao.
* Precos ficam versionados ou centralizados.

---

## Tarefa 13: Metrica FinOps

**Objetivo:** Criar evento de metrica da chamada.

### Passos
1. Criar entidade `FinOpsMetric`.
2. Preencher modelo, tokens, cache status, custo, economia e latencia.
3. Associar `request_id`.
4. Testar metricas para cache hit e miss.

### Qualidade Esperada
* Entidade sem dependencia de banco.
* Campos obrigatorios explicitos.
* Calculo de economia testado.

---

## Tarefa 14: Persistencia Assincrona de Metricas

**Objetivo:** Salvar metricas sem afetar a resposta HTTP.

### Passos
1. Criar interface `MetricsRepository`.
2. Criar implementacao Postgres.
3. Criar mecanismo de background task.
4. Tratar falha de banco com log estruturado.
5. Testar que erro de persistencia nao altera resposta principal.

### Qualidade Esperada
* Caso de uso nao conhece driver SQL.
* Escrita assincrona e tolerante a falhas.
* Migracao SQL documentada.

---

## Tarefa 15: Observabilidade Basica

**Objetivo:** Facilitar diagnostico sem vazar dados sensiveis.

### Passos
1. Gerar `request_id` por chamada.
2. Adicionar headers de observabilidade.
3. Criar logs estruturados.
4. Remover prompts completos dos logs.
5. Testar presenca de headers em sucesso e erro.

### Qualidade Esperada
* Logs curtos e correlacionaveis.
* Segredos mascarados.
* Headers estaveis para clientes e testes.

---

## Tarefa 16: Smoke Test do Fluxo Principal

**Objetivo:** Validar o fluxo completo local.

### Passos
1. Subir aplicacao local.
2. Executar health check.
3. Executar chamada nao autenticada.
4. Executar cache miss autenticado.
5. Repetir chamada para validar cache hit.

### Qualidade Esperada
* Smoke test pode ser executado por comando simples.
* Resultado deve mostrar status HTTP e headers principais.
* Nao depende de dados manuais escondidos.

---

## Tarefa 17: Containerização e Deploy Alternativo

**Objetivo:** Permitir empacotar o app Python em container para deploy em Azure Container Apps ou ambiente compatível.

### Passos
1. Criar `Dockerfile` enxuto para produção.
2. Criar `.dockerignore`.
3. Garantir que o container respeite a variável `PORT`.
4. Documentar build e execução local.
5. Documentar deploy alternativo no Azure Container Apps.
6. Reforçar que segredos devem ser configurados fora da imagem.

### Qualidade Esperada
* Imagem sobe localmente com `/health`.
* Nenhum segredo é copiado para a imagem.
* README explica App Service e Container Apps como alternativas.

---

## Tarefa 18: Adaptador Real para OpenAI

**Objetivo:** Permitir que o gateway encaminhe chamadas reais para a OpenAI quando `OPENAI_API_KEY` estiver configurada.

### Passos
1. Adicionar dependencia HTTP assíncrona ou SDK oficial da OpenAI, mantendo o dominio desacoplado.
2. Criar `OpenAIProviderClient` implementando `ProviderClient`.
3. Ler credencial exclusivamente de `AppSettings.openai_api_key`.
4. Encaminhar payload de `POST /v1/chat/completions` para o endpoint real da OpenAI.
5. Preservar status code e corpo de resposta quando a chamada for bem-sucedida.
6. Mapear erros, rate limits e timeouts para `ProviderError` com mensagem segura.
7. Adicionar testes com cliente HTTP fake, sem chamar a OpenAI real.

### Qualidade Esperada
* Nenhuma chave real aparece em logs, respostas ou fixtures.
* Testes nao dependem de internet.
* O adaptador fica em `infrastructure`, nao em `domain` ou `application`.
* O contrato `ProviderClient` continua pequeno e substituivel.

---

## Tarefa 19: Bootstrap de Dependencias Reais por Configuracao

**Objetivo:** Fazer o app usar dependencias reais automaticamente quando as configuracoes estiverem presentes.

### Passos
1. Criar uma factory de aplicacao ou modulo de bootstrap para montar dependencias a partir de `AppSettings`.
2. Em `development`, manter defaults seguros e permitir provider fake/unconfigured para testes locais.
3. Em `staging` e `production`, exigir `OPENAI_API_KEY`, `REDIS_URL`, `DATABASE_URL` e `GATEWAY_API_KEYS`.
4. Instanciar `OpenAIProviderClient` quando `OPENAI_API_KEY` estiver presente.
5. Instanciar `RedisCacheStore.from_url(settings.redis_url)` quando `REDIS_URL` estiver presente.
6. Instanciar `PostgresMetricsRepository.from_database_url(settings.database_url)` quando `DATABASE_URL` estiver presente.
7. Atualizar `main.py` para usar a factory real.
8. Adicionar testes para combinacoes de ambiente com e sem configuracoes reais.

### Qualidade Esperada
* Falhas de configuracao devem ser claras e nao expor segredos.
* Testes unitarios nao devem abrir conexoes reais.
* A aplicacao continua facil de montar com fakes em testes.
* O bootstrap deve ser a unica camada que conhece todas as implementacoes concretas.

---

## Tarefa 20: Integrar Retry ao Provider Real

**Objetivo:** Garantir que chamadas reais ao provedor usem retry com backoff e jitter.

### Passos
1. Envolver `OpenAIProviderClient` com `RetryingProviderClient` no bootstrap.
2. Usar `MAX_RETRY_ATTEMPTS` para configurar a politica de retry.
3. Garantir que apenas HTTP 408, 429 e 5xx sejam retentados.
4. Evitar sleeps reais em testes usando sleeper fake.
5. Testar sucesso apos retry e falha final no fluxo montado.

### Qualidade Esperada
* Erros 4xx de cliente nao devem ser retentados.
* O timeout total deve ser coerente com `PROVIDER_TIMEOUT_SECONDS`.
* A regra de retry continua isolada e testavel.

---

## Tarefa 21: Propagar Contagem Real de Retries

**Objetivo:** Fazer o header `X-Retry-Count` refletir quantas tentativas extras foram executadas.

### Passos
1. Estender o resultado do provider ou criar metadados de chamada sem quebrar o contrato atual.
2. Registrar quantos retries foram executados pelo `RetryingProviderClient`.
3. Propagar a contagem ate `ChatCompletionResult`.
4. Retornar `X-Retry-Count` com o valor real.
5. Adicionar testes de cache miss sem retry, sucesso apos retry e falha final.

### Qualidade Esperada
* Cache hit deve retornar `X-Retry-Count: 0`.
* A contagem nao deve depender de parsing de logs.
* Mudanca deve preservar compatibilidade com providers fake nos testes.

---

## Tarefa 22: Smoke Test com Redis Real Opcional

**Objetivo:** Validar cache miss e cache hit usando uma instancia Redis real quando `REDIS_URL` estiver configurado.

### Passos
1. Criar script ou teste marcado como integracao.
2. Pular automaticamente quando `REDIS_URL` nao estiver configurado.
3. Usar uma chave/prefixo isolado para evitar colisao com dados reais.
4. Executar duas chamadas identicas e validar `MISS` seguido de `HIT`.
5. Limpar chaves de teste quando possivel.
6. Documentar o comando no README.

### Qualidade Esperada
* O teste nao deve exigir prompt ou segredo de provedor real.
* Falha do Redis deve produzir diagnostico claro.
* Nao deve apagar chaves fora do prefixo de teste.

---

## Tarefa 23: Smoke Test com Postgres ou Neon Real Opcional

**Objetivo:** Validar persistencia de metricas em banco real quando `DATABASE_URL` estiver configurado.

### Passos
1. Criar script ou teste marcado como integracao.
2. Pular automaticamente quando `DATABASE_URL` nao estiver configurado.
3. Garantir que a migracao `001_create_finops_metrics.sql` esteja aplicada ou orientar a aplicacao.
4. Executar uma chamada que gere metrica.
5. Consultar `tb_finops_metrics` por `request_id` ou outro identificador de teste.
6. Documentar o comando no README.

### Qualidade Esperada
* O teste nao deve depender de dashboard externo.
* Erros de schema devem ser claros.
* A escrita de metrica continua sem bloquear a resposta principal.

---

## Tarefa 24: Benchmark de Cache Hit com Redis Real

**Objetivo:** Medir latencia de cache hit em Redis real antes de publicar numeros como "abaixo de 50ms".

### Passos
1. Criar script de benchmark simples e reproduzivel.
2. Exigir `REDIS_URL` ou pular com mensagem clara.
3. Aquecer o cache antes da medicao.
4. Medir varias chamadas de cache hit.
5. Reportar p50, p95, p99 e media.
6. Documentar ambiente, comando e interpretacao do resultado.

### Qualidade Esperada
* O benchmark nao deve chamar provedor pago.
* Resultados devem deixar claro se sao locais, Azure, Redis Free Tier ou outro ambiente.
* README e artigo so devem citar numeros medidos.
