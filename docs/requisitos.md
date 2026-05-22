# Documento de Requisitos Técnicos (PRD)
## Projeto: FinOpsTokenSaver

---

### 1. Visão Geral do Produto
O **FinOpsTokenSaver** é um gateway de inteligência artificial (AI Gateway) de alta performance que funciona como um proxy reverso entre as aplicações clientes e os provedores oficiais de Modelos de Linguagem (LLMs), tais como OpenAI, Anthropic e Google Gemini. 

O foco central da solução é duplo:
1. **FinOps (Otimização Financeira):** Reduzir de forma agressiva os custos de infraestrutura com IA através da implementação de uma camada híbrida de cache (exato e semântico), evitando chamadas redundantes e caras para os provedores externos.
2. **Resiliência Arquitetural:** Proteger os sistemas de falhas de rede, indisponibilidade temporária e limites de requisição (*Rate Limiting* / HTTP 429), utilizando algoritmos de tratamento de erros transparentes para o cliente final.

O grande diferencial técnico deste projeto é a sua capacidade de operar de maneira robusta, escalável e segura sendo hospedado inteiramente em **camadas de infraestrutura 100% gratuitas**.

---

### 2. Objetivos Principais
* **Mitigação de Custos com Tokens:** Economizar entre 20% e 40% em cenários corporativos reais através do reaproveitamento de respostas salvas em cache.
* **Transparência de Integração:** Oferecer compatibilidade total com os SDKs oficiais de mercado (ex: formato de contratos da OpenAI), exigindo apenas a alteração da URL base (`BASE_URL`) na aplicação cliente.
* **Alta Disponibilidade e Resiliência:** Eliminar interrupções no fluxo de processamento causadas por limites de requisições excedidos dos provedores de LLM.
* **Métricas FinOps em Tempo Real:** Fornecer dados claros de auditoria que permitam calcular o custo real das operações e o ROI (Retorno sobre Investimento) gerado pela economia do gateway.

---

### 3. Restrições de Arquitetura (Camada Gratuita)
O design do sistema foi estritamente planejado para se adequar e respeitar as limitações das seguintes plataformas sem gerar custos operacionais:

| Componente | Provedor / Tecnologia | Limitações da Camada Gratuita | Estratégia de Mitigação |
| :--- | :--- | :--- | :--- |
| **Hospedagem & Compute** | Azure App Service (Plano F1) | • 60 minutos de CPU por dia<br>• 1 GB de memória RAM compartilhada<br>• Sem suporte a tráfego persistente massivo | Utilização de tecnologias assíncronas com I/O não-bloqueante (FastAPI/Python, Go ou Node.js). Otimização extrema de memória para manter o processo base abaixo de 150MB. |
| **Camada de Cache** | Redis (Free Tier - ex: Upstash / Redis Labs) | • Memória limitada (30MB a 100MB)<br>• Limite diário de requisições / comandos | Configuração de TTL (Time-To-Live) curto (máximo de 12h) e aplicação rígida da política de expulsão `allkeys-lru` (remover chaves menos utilizadas recentemente). |
| **Persistência de Métricas** | Neon Serverless Postgres | • 0.5 GiB de armazenamento de dados<br>• Auto-suspend (interrupção do compute) após 5-10 min de inatividade | Escrita puramente assíncrona baseada em filas/background tasks para não travar a requisição principal. Suporte a conexões dinâmicas para tolerar o *Cold Start* do banco. |

---

### 4. Fluxo de Dados e Arquitetura Lógica

1. **Requisição do Cliente:** A aplicação cliente envia um payload de chat completion (ex: `/v1/chat/completions`) direcionado ao **FinOpsTokenSaver** na Azure.
2. **Camada de Interceptação e Sanitização:** O gateway intercepta a chamada, valida a API Key interna (segurança) e sanitiza o prompt.
3. **Verificação de Cache (Redis):** * É gerado um hash único do prompt (SHA-256).
   * O Redis é consultado para verificar se já existe uma resposta idêntica associada àquele hash.
   * **CACHE HIT:** Se encontrado, o gateway extrai a resposta do Redis, calcula a latência simulada de entrega rápida (< 50ms) e retorna os dados imediatamente para o cliente. Custo final da requisição = $0.00.
   * **CACHE MISS:** Se não encontrado, o fluxo segue para o Provedor de IA.
4. **Chamada ao Provedor Externo (LLM):** O gateway repassa a requisição original com as credenciais oficiais de produção para o provedor (ex: OpenAI).
5. **Módulo de Resiliência (Tratamento 429/5xx):** Se o provedor retornar um erro HTTP 429 (Rate Limit) ou 5xx (Erro do Servidor), o gateway intercepta a falha e dispara tentativas automáticas utilizando o algoritmo de *Exponential Backoff com Jitter* antes de admitir a falha ao cliente.
6. **Entrega e Persistência Assíncrona:** Com a resposta bem-sucedida em mãos:
   * A resposta é devolvida imediatamente ao cliente (para minimizar o tempo de espera).
   * Uma tarefa em plano de fundo (*Background Task*) salva a resposta no Redis com o respectivo TTL.
   * A mesma tarefa computa os tokens gastos (`prompt_tokens` e `completion_tokens`), estima a economia financeira baseada na tabela de preços do modelo, e salva uma linha de log de auditoria no **Neon Postgres**.

---

### 5. Requisitos Funcionais (RF)

#### RF-001: Compatibilidade Total com APIs de Mercado
* **Descrição:** O Gateway deve expor rotas que mimetizem exatamente a assinatura das rotas de chat e completude de texto das principais IAs de mercado.
* **Critério de Aceite:** Uma aplicação que usa a biblioteca oficial da OpenAI configurada com `openai.base_url = "https://finopstokensaver.azurewebsites.net/v1"` deve funcionar sem modificar nenhuma outra linha de código.

#### RF-002: Cache de Resposta por Identidade Exata (Curto Prazo)
* **Descrição:** Implementação de cache de chave-valor simples onde a chave é o hash determinístico do array de mensagens (`messages`) e do modelo solicitado (`model`).
* **Critério de Aceite:** Se duas requisições idênticas forem enviadas dentro da janela do TTL, a segunda deve ser atendida pelo Redis em menos de 100ms.

#### RF-003: Algoritmo de Resiliência (Exponential Backoff + Jitter)
* **Descrição:** Em caso de falha de conexão ou Rate Limit, o sistema deve pausar e tentar novamente de forma progressiva.
* **Fórmula Aplicada:** `Tempo de Espera = 2^tentativa + jitter_aleatorio`
* **Critério de Aceite:** O gateway deve realizar no máximo 3 tentativas. Se a terceira falhar, deve repassar o erro estruturado para o cliente. O tempo de execução das tentativas não deve causar estouro de timeout do Azure App Service.

#### RF-004: Pipeline de Métricas FinOps Assíncrono
* **Descrição:** Coleta e gravação de metadados financeiros das chamadas sem introduzir latência na resposta do usuário.
* **Critério de Aceite:** O tempo gasto para persistir os dados no Neon Postgres não pode impactar o tempo de resposta enviado ao cliente (deve rodar após o fechamento da conexão HTTP ou em thread separada).

---

### 6. Requisitos Não-Funcionais (RNF)

#### RNF-001: Desempenho e Consumo de Recursos (Azure F1)
* **Descrição:** O software deve ter uma pegada de memória e uso de CPU extremamente enxuta para evitar a suspensão ou limitação do plano gratuito da Azure.
* **Métrica:** O uso de memória RAM em modo estável (repouso) não deve exceder 150MB. A aplicação deve utilizar concorrência baseada em eventos assíncronos (I/O Bound).

#### RNF-002: Gerenciamento de Limites do Redis
* **Descrição:** Prevenir erros de falta de memória (*OOM - Out of Memory*) na instância gratuita do Redis.
* **Métrica:** Configurar todas as chaves criadas com um tempo de expiração padrão (TTL) ajustável (recomendado: 43200 segundos / 12 horas). Definir a política global do Redis para `allkeys-lru`.

#### RNF-003: Tolerância a Cold Starts do Banco Neon
* **Descrição:** Como o banco de dados gratuito Neon entra em repouso após inatividade, a primeira requisição do dia pode demorar alguns segundos para inicializar a conexão com o banco de dados.
* **Métrica:** O gateway deve gerenciar as conexões através de um pool resiliente. Caso o Neon esteja inicializando, a tarefa de background de métricas deve aguardar ou reter o log em memória temporária para tentar novamente, impedindo que o fluxo principal da API seja travado ou derrubado por causa do banco de dados.

---

### 7. Modelo de Dados Relacional (Neon Postgres)

Abaixo está a estrutura SQL DDL necessária para inicializar o esquema de tabelas no banco de dados Neon para suportar a auditoria de FinOps:

```sql
-- Criação da tabela de auditoria de métricas e economia de tokens
CREATE TABLE tb_finops_metrics (
    id SERIAL PRIMARY KEY,
    request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    model_name VARCHAR(100) NOT NULL,
    prompt_tokens INT NOT NULL,
    completion_tokens INT NOT NULL,
    is_cache_hit BOOLEAN NOT NULL,
    estimated_cost_usd NUMERIC(12, 6) NOT NULL, -- O custo real que seria cobrado pelo provedor externo
    saved_cost_usd NUMERIC(12, 6) NOT NULL,     -- O valor economizado caso tenha sido um Cache Hit
    latency_ms INT NOT NULL                     -- Tempo total de processamento da requisição interna
);

-- Índices recomendados para otimização de consultas e dashboards futuros
CREATE INDEX idx_metrics_timestamp ON tb_finops_metrics(request_timestamp);
CREATE INDEX idx_metrics_cache_hit ON tb_finops_metrics(is_cache_hit);
```

---

### 8. Escopo do MVP

O MVP deve validar a proposta central do produto com o menor conjunto de funcionalidades que gere economia real e mantenha compatibilidade operacional com clientes que usam SDKs no formato OpenAI.

#### Incluido no MVP
* Proxy para `POST /v1/chat/completions`.
* Autenticacao do cliente via chave interna do gateway.
* Encaminhamento inicial para um provedor LLM configuravel, com OpenAI como primeiro adaptador.
* Cache exato em Redis baseado em payload canonico.
* Retry com exponential backoff e jitter para falhas transientes.
* Registro assincrono de metricas FinOps no Postgres.
* Endpoint simples de saude para deploy e monitoramento.
* Testes automatizados de dominio, cache, resiliencia e contrato HTTP.

#### Fora do MVP
* Cache semantico com embeddings.
* Dashboard web completo.
* Multi-tenant com isolamento por organizacao.
* Streaming SSE em tempo real.
* Fallback automatico entre provedores diferentes.
* Rate limiting proprio por cliente.

Esses itens podem entrar no roadmap posterior, desde que nao prejudiquem a simplicidade operacional exigida pela camada gratuita.

---

### 9. Requisitos Funcionais Detalhados

#### RF-005: Autenticacao de Clientes
* **Descricao:** O gateway deve aceitar apenas chamadas com credencial valida enviada no cabecalho `Authorization: Bearer <gateway_api_key>`.
* **Criterio de Aceite:** Requisicoes sem chave, com chave vazia ou chave invalida devem retornar `401 Unauthorized` sem acionar cache, banco ou provedor externo.
* **Observacao de Design:** A validacao deve estar isolada em componente proprio para permitir troca futura por API keys por tenant.

#### RF-006: Encaminhamento Seguro para o Provedor
* **Descricao:** O cliente nao deve enviar diretamente a chave real do provedor LLM. O gateway deve usar credenciais do ambiente de execucao.
* **Criterio de Aceite:** Logs, metricas e respostas de erro nunca devem expor `OPENAI_API_KEY`, chaves de Redis, strings de conexao ou headers sensiveis.

#### RF-007: Canonicalizacao do Payload para Cache
* **Descricao:** A chave de cache deve ser derivada de uma representacao canonica do payload relevante.
* **Campos Obrigatorios na Chave:** `provider`, `model`, `messages`, `temperature`, `top_p`, `max_tokens`, `response_format`, `tools` e `tool_choice`, quando presentes.
* **Criterio de Aceite:** Dois payloads semanticamente iguais, mas com ordem diferente de propriedades JSON, devem gerar a mesma chave. Dois payloads com parametros de geracao diferentes devem gerar chaves diferentes.

#### RF-008: Politica de Cacheabilidade
* **Descricao:** O gateway deve decidir explicitamente quando uma resposta pode ser cacheada.
* **Deve Cachear:** Respostas HTTP 2xx completas, sem streaming, sem erro de ferramenta pendente e com corpo valido.
* **Nao Deve Cachear:** Erros do provedor, requisicoes com `stream=true`, respostas incompletas, payloads acima do limite configurado e chamadas marcadas com header `X-Cache-Bypass: true`.
* **Criterio de Aceite:** Uma resposta de erro nunca deve ser retornada posteriormente como cache hit.

#### RF-009: Cabecalhos de Observabilidade
* **Descricao:** O gateway deve devolver metadados leves em headers HTTP para facilitar diagnostico.
* **Headers Minimos:** `X-Cache-Status` (`HIT`, `MISS`, `BYPASS`), `X-Request-Id`, `X-Provider`, `X-Retry-Count` e `X-Gateway-Latency-Ms`.
* **Criterio de Aceite:** Todo retorno, inclusive erro tratado, deve conter `X-Request-Id`.

#### RF-010: Health Check
* **Descricao:** O gateway deve expor `GET /health`.
* **Criterio de Aceite:** O endpoint deve responder rapidamente sem depender de chamada ao provedor LLM. Verificacoes profundas de Redis e Postgres devem ser opcionais para nao consumir recursos desnecessarios.

#### RF-011: Precificacao e Economia Estimada
* **Descricao:** O sistema deve calcular custo estimado com base em tabela versionada de precos por modelo.
* **Criterio de Aceite:** Quando o modelo nao estiver cadastrado, o registro de metrica deve marcar o custo como `0` e sinalizar o motivo em campo observavel ou log estruturado, sem falhar a requisicao principal.

#### RF-012: Erros Compatíveis com Cliente OpenAI
* **Descricao:** Respostas de erro devem manter formato previsivel e proximo ao padrao OpenAI.
* **Criterio de Aceite:** Erros de validacao, autenticacao, timeout e provedor devem conter `error.message`, `error.type`, `error.code` e status HTTP coerente.

---

### 10. Requisitos Nao-Funcionais Detalhados

#### RNF-004: Configuracao por Ambiente
* **Descricao:** Toda configuracao operacional deve vir de variaveis de ambiente.
* **Variaveis Minimas:** `GATEWAY_API_KEYS`, `OPENAI_API_KEY`, `REDIS_URL`, `DATABASE_URL`, `CACHE_TTL_SECONDS`, `PROVIDER_TIMEOUT_SECONDS`, `MAX_RETRY_ATTEMPTS` e `LOG_LEVEL`.
* **Metrica:** A aplicacao deve iniciar com erro claro quando configuracoes obrigatorias estiverem ausentes.

#### RNF-005: Testabilidade
* **Descricao:** Regras de dominio nao devem depender diretamente de FastAPI, Redis, Postgres ou SDK externo.
* **Metrica:** Componentes de cache key, politica de cache, calculo de custo e retry devem possuir testes unitarios sem rede.

#### RNF-006: Observabilidade Enxuta
* **Descricao:** Logs devem ser estruturados, curtos e suficientes para correlacionar requisicoes.
* **Metrica:** Cada requisicao deve registrar `request_id`, `provider`, `model`, `cache_status`, `latency_ms`, `retry_count` e status final. Prompts completos nao devem ser logados por padrao.

#### RNF-007: Privacidade de Prompts
* **Descricao:** O projeto deve tratar prompts como dados potencialmente sensiveis.
* **Metrica:** Logs devem registrar apenas hashes, tamanhos e metadados. Conteudo integral de prompt so pode aparecer em ambiente local de desenvolvimento quando configurado explicitamente.

#### RNF-008: Limites de Payload
* **Descricao:** O gateway deve rejeitar payloads excessivos antes de acionar provedor ou cache.
* **Metrica:** O limite inicial recomendado e 1 MB por requisicao, configuravel por ambiente.

#### RNF-009: Portabilidade
* **Descricao:** O projeto deve rodar localmente com dependencias substituiveis.
* **Metrica:** Deve existir modo de desenvolvimento com Redis/Postgres locais ou mocks, sem exigir Azure.

---

### 11. Decisoes de Design e Qualidade de Codigo

O codigo deve ser organizado para preservar regras de negocio independentes de frameworks e infraestrutura. O objetivo e facilitar testes, evolucao para novos provedores e controle de custo operacional.

#### SOLID
* **Single Responsibility:** Separar controladores HTTP, autenticacao, cache, adaptadores de provedor, calculo de preco, persistencia de metricas e politicas de retry.
* **Open/Closed:** Novos provedores devem ser adicionados via adaptadores que implementam contrato comum, sem alterar o fluxo principal do caso de uso.
* **Liskov Substitution:** Adaptadores de provedores devem respeitar o mesmo contrato de entrada, saida e erro.
* **Interface Segregation:** Interfaces pequenas como `CacheStore`, `ProviderClient`, `MetricsRepository`, `PricingCatalog` e `RetryPolicy`.
* **Dependency Inversion:** Casos de uso dependem de abstracoes; FastAPI, Redis, Postgres e SDKs oficiais ficam nas bordas.

#### Clean Code
* Nomes devem expressar intencao de negocio: `CacheDecision`, `CanonicalPayload`, `FinOpsMetric`, `ProviderResponse`.
* Funcoes devem ser pequenas e ter um nivel claro de abstracao.
* Erros esperados devem virar tipos ou excecoes de dominio, nao strings soltas.
* Configuracoes magicas devem ser nomeadas e centralizadas.

#### Design Patterns Recomendados
* **Adapter:** Integracao com OpenAI, Anthropic e Gemini.
* **Strategy:** Politicas de retry, cacheabilidade e precificacao por modelo.
* **Repository:** Persistencia de metricas.
* **Decorator ou Middleware:** Autenticacao, request id, logging e medicao de latencia.
* **Factory:** Criacao de clientes externos a partir de configuracao.

#### Object Calisthenics
* Evitar classes grandes; uma classe deve representar uma responsabilidade concreta.
* Preferir objetos de valor para `CacheKey`, `Money`, `TokenUsage`, `RequestId` e `Latency`.
* Evitar encadeamentos profundos; expor metodos de intencao.
* Encapsular colecoes quando houver regra associada, por exemplo uma colecao de mensagens canonicas.
* Evitar `else` desnecessario usando retornos antecipados em validacoes simples.

---

### 12. Contratos Minimos de API

#### `POST /v1/chat/completions`
* **Entrada:** Corpo compativel com Chat Completions da OpenAI.
* **Saida Cache Miss:** Resposta do provedor preservada, acrescida de headers de observabilidade.
* **Saida Cache Hit:** Corpo previamente armazenado, preservando formato original.
* **Status Esperados:** `200`, `400`, `401`, `408`, `429`, `500`, `502`, `503`.

#### `GET /health`
* **Resposta 200:**

```json
{
  "status": "ok",
  "service": "finops-token-saver"
}
```

---

### 13. Riscos e Mitigacoes

| Risco | Impacto | Mitigacao |
| :--- | :--- | :--- |
| Redis gratuito atingir limite | Perda de cache e aumento de custo | TTL curto, tamanho maximo de item, politica LRU e fallback transparente para provedor |
| Neon em cold start | Perda ou atraso de metricas | Escrita assincrona, retry interno e logs de falha sem afetar resposta |
| Mudanca de contrato dos provedores | Quebra de compatibilidade | Adaptadores isolados e testes de contrato |
| Vazamento de prompt em logs | Risco de seguranca e privacidade | Logs sem corpo de prompt por padrao |
| Cache indevido de resposta variavel | Resposta incorreta ao cliente | Chave canonica incluindo parametros de geracao e politica explicita de cacheabilidade |

---

### 14. Indicadores de Sucesso

* Taxa de cache hit acima de 20% em workloads repetitivos.
* Latencia p95 de cache hit abaixo de 100 ms em ambiente com Redis saudavel.
* Zero chamadas ao provedor em requisicoes autenticadas invalidas.
* Zero exposicao de segredos em logs e respostas.
* Cobertura de testes nos componentes de dominio criticos.
