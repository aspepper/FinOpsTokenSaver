### Resumo Arquitetural do Projeto (Para você começar a codificar)

Para garantir que o projeto funcione perfeitamente dentro dos limites das camadas gratuitas, a arquitetura deve ser extremamente leve e eficiente:

**1. Proxy Reverso / Camada de Aplicação (Azure App Service - Camada F1):**
*   **Abordagem:** Desenvolver o gateway usando uma tecnologia de I/O não-bloqueante de alta performance (como **FastAPI/Python**, **Node.js/TypeScript** ou **Go**). Isso garante que o contêiner gratuito da Azure aguente um bom volume de requisições simultâneas sem estourar a memória RAM limitante da camada livre.
*   **Comportamento:** A aplicação recebe a chamada do cliente (ex: formato padrão da OpenAI), verifica o cache, e se não houver, repassa para a API de IA real.

**2. Camada de Cache Semântico (Redis Free Tier):**
*   **Estratégia de Economia:** Armazenar hashes de perguntas exatas ou resultados de buscas semânticas recentes. Como a camada gratuita do Redis tem limite de memória, configure uma política de **LFU (Least Frequently Used)** ou **LRU (Least Recently Used)** com tempo de expiração (TTL) curto para reaproveitar o espaço constantemente.

**3. Persistência e Auditoria de Custos (Neon DB - Serverless Postgres):**
*   **Armazenamento Inteligente:** O banco não deve ser usado no meio da requisição de tempo real para não gerar gargalos. Ele será usado de forma assíncrona para registrar o histórico de uso, métricas de latência e **grana economizada** (FinOps). O Neon é perfeito aqui porque entra em *idle* (suspensão) quando não está recebendo requisições, não consumindo suas horas gratuitas à toa.

---

## Direcionamento de Implementação

A implementação deve começar pelo MVP descrito em `docs/requisitos.md` e seguir o roadmap em `docs/roadmap.md`. O objetivo é manter o núcleo do gateway pequeno, testável e desacoplado das tecnologias externas.

### Organização Recomendada
* **API:** rotas HTTP, validação superficial de entrada, headers de resposta e mapeamento de erros.
* **Application:** casos de uso, orquestração de cache, provedor, retry e métricas.
* **Domain:** objetos de valor, políticas de cache, cálculo de custo, decisões de retry e regras puras.
* **Infrastructure:** Redis, Postgres, SDKs de provedores, logs estruturados e leitura de configuração.

### Fluxo Principal do MVP
1. Receber `POST /v1/chat/completions`.
2. Validar API key interna do gateway.
3. Gerar `request_id`.
4. Avaliar se a requisição pode usar cache.
5. Gerar chave canônica e consultar Redis.
6. Em cache hit, retornar a resposta cacheada com headers de observabilidade.
7. Em cache miss, chamar o provedor usando adapter.
8. Aplicar retry apenas em falhas transientes.
9. Retornar resposta ao cliente.
10. Salvar cache e métrica FinOps de forma assíncrona.

### Documentos de Apoio
* `docs/requisitos.md`: PRD enriquecido, escopo do MVP, requisitos detalhados, contratos e riscos.
* `docs/roadmap.md`: fases de entrega e critérios de pronto.
* `docs/tarefas-codex.md`: tarefas pequenas para desenvolvimento incremental pelo Codex.
* `docs/guia-qualidade-codigo.md`: regras práticas de SOLID, Clean Code, Design Patterns e Object Calisthenics.
