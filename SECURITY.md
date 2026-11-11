# Security model

## Intended scope

Evidence RAG is a single-user, local research workbench. Bind to loopback. Code publication on GitHub does not deploy a public service. Host/origin checks reduce browser-to-local attacks but do not provide user authentication. Except for Agent Permit's role-separated routes, APIs are local and unauthenticated. Before shared deployment, add identity, authorization, TLS, quotas, retention and tenant isolation.

## Trust boundaries

| Boundary | Control | Residual risk |
| --- | --- | --- |
| Browser → API | Local binding, trusted Host and Origin, strict body schema, 128 KiB limit | Local programs can still call the API; no global rate limit |
| Untrusted text → HTML | React text rendering; no raw HTML injection | Dependencies and browser extensions remain trusted |
| API → SQLite | Parameterized SQL, WAL, explicit write transactions | Local operator can read/modify DB; no at-rest encryption |
| Audit events → evidence | Metadata-only records, SHA256 chaining | No external anchor; truncation and complete rewrite undetectable |
| Server → optional model | Operator-controlled endpoint, bounded timeout, no redirects | Misconfigured endpoint or malicious provider still matters |

`TRUSTED_HOSTS` is an operator environment setting, comma-separated; defaults to localhost, 127.0.0.1 and testserver. Do not set a wildcard for a shared deployment. `APP_DB` chooses a local database path. Keep `data/`, `.env`, session capabilities and reviewer keys out of Git.

## Project-specific assumptions

- 引用逐字匹配只验证出处完整性，不证明事实真实、问题相关或语义蕴含。
- 隔离器是启发式检查，可能漏掉语义投毒，也可能隔离教学材料。
- 检索对整个小型语料重新评分，适合本地研究规模，未做大规模或多租户优化。
- 默认模式返回原文，不伪装成生成式模型回答；Ollama 模式依赖本地模型，失败明确返回 502/503。

## Reporting

Use GitHub private vulnerability reporting if enabled. Otherwise open an issue containing only a minimal synthetic reproduction, never real secrets or customer data. This project does not claim production readiness or comprehensive LLM safety guarantees.
