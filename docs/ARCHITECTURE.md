# Architecture and extension points

## Data flow

```mermaid
flowchart LR
    Document --> SHA256
    SHA256 --> Quarantine
    Quarantine -->|clean| Chunks
    Query --> BM25
    Query --> Trigram
    BM25 --> RRF
    Trigram --> RRF
    Chunks --> RRF
    RRF --> QuoteSelection
    QuoteSelection --> Verification
    Verification --> AnswerOrAbstain
```

## Module boundaries

`app/main.py` owns Pydantic contracts and HTTP behavior. The domain module owns scoring, retrieval, authorization, evaluation or privacy state. `app/platform.py` owns bounded HTTP bodies, local trust checks, metadata audit persistence and frontend mounting. The React workbench is a client of the same public API documented by FastAPI.

SQLite transactions use parameterized queries and close their connections at scope exit. WAL is selected for local read/write concurrency. Domain state and audit records are separate concerns: the audit append is not generally atomic with a domain state change. Deploy one process for Privacy Relay's in-memory vault.

## Decisions

| Decision | Reason | Tradeoff |
| --- | --- | --- |
| Small independent repository | Easy to clone, review, run and extend | Common workbench infrastructure is duplicated |
| FastAPI + React | Typed request validation and familiar full-stack interfaces | Shared types are not code-generated yet |
| SQLite | Zero external service and deterministic fixtures | Not a high-throughput multi-tenant design |
| Offline default | Reproducible demos without credentials or paid inference | Does not prove behavior of a live model |
| Inspectable algorithms | Failures can be explained during review | Baselines have documented recall/precision limits |

## Extension plan

1. 引入 embedding 召回与 cross-encoder 重排，报告 Recall@k、MRR、nDCG 和拒答准确率。
2. 加入主张级引用与独立蕴含验证器，区分“出处存在”和“出处支持结论”。
3. 支持签名来源、文档更新传播、租户 ACL 过滤和索引增量更新。

Before implementing an extension, define its acceptance metric, failure budget and comparison baseline. Keep transport errors separate from successful defenses and keep external validation data separate from development fixtures.
