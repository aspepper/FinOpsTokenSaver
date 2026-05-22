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
