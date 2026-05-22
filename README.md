# FinOpsTokenSaver 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Azure](https://img.shields.io/badge/Hosted_on-Azure_App_Service-0089D6?logo=microsoft-azure)](https://azure.microsoft.com/)
[![Redis](https://img.shields.io/badge/Cache-Redis_Free_Tier-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Neon](https://img.shields.io/badge/Database-Neon_Postgres-00E599?logo=postgresql&logoColor=black)](https://neon.tech/)

O **FinOpsTokenSaver** é um gateway de IA e proxy reverso inteligente de alta performance, projetado especificamente para reduzir custos de tokens corporativos e aumentar a resiliência de aplicações que utilizam LLMs (como OpenAI, Gemini e Anthropic).

Toda a arquitetura foi desenhada de forma extremamente leve para rodar de maneira robusta e estável dentro dos limites de **infraestrutura 100% gratuita** (Azure Free F1, Neon Serverless e Redis Free Tier).

---

## 💡 Por que o FinOpsTokenSaver?

Integrar inteligência artificial em sistemas corporativos traz dois grandes problemas: **custos imprevisíveis de tokens** e **erros de Rate Limiting (HTTP 429)**. O FinOpsTokenSaver atua como um intermediário inteligente para resolver ambos:

*   **Cache Semântico e Exato (FinOps):** Economiza até 40% em chamadas redundantes para as APIs pagas, buscando respostas idênticas ou muito similares direto no Redis antes de gastar tokens.
*   **Resiliência Nativa:** Implementa algoritmos de *Exponential Backoff com Jitter* para tratar erros 429 de forma transparente, garantindo que o usuário final nunca sofra com instabilidades temporárias dos provedores.
*   **Auditoria Assíncrona de Custos:** Salva métricas de consumo de tokens e a exata quantia de dinheiro economizada em um banco Neon Postgres de forma assíncrona, mantendo o tempo de resposta do proxy abaixo dos 50ms no *Cache Hit*.

---

## 🛠️ Arquitetura do Sistema

O fluxo de dados foi projetado para respeitar os limites de memória da camada gratuita da Azure (1GB RAM compartilhado):

1. **Cliente** envia a requisição alterando apenas a `BASE_URL` para o endereço do Gateway.
2. O Gateway valida se a resposta já existe no **Redis** (TTL curto e política LRU para otimizar espaço).
3. Se houver um *Cache Miss*, a requisição é enviada ao provedor oficial.
4. Ao retornar, os dados são cacheados e uma task assíncrona grava as métricas financeiras no **Neon Postgres**.

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

---

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---
Desenvolvido por [Alex Pimenta](https://www.linkedin.com/in/alexpimentadev/?locale=pt) - Vamos nos conectar no LinkedIn!
