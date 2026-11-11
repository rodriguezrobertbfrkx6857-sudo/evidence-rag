import { useState, useEffect } from "react";
import { ArrowRight, BookOpen } from "lucide-react";
import { Shell, Card, Metrics, api, Json, ErrorBox, Empty, Badge } from "./ui";
export default function App() {
  const [query, setQuery] = useState("Atlas 的对话数据保留多久？"),
    [mode, setMode] = useState("extractive"),
    [result, setResult] = useState<any>(null),
    [docs, setDocs] = useState<any[]>([]),
    [title, setTitle] = useState(""),
    [content, setContent] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function refresh() {
    setDocs((await api("/documents")).documents);
  }
  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
  }, []);
  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Shell
      title="Evidence RAG"
      subtitle="让每一条回答都有出处。混合检索、投毒隔离、逐字引用校验，以及证据不足时的主动拒答。"
      number="02"
    >
      <Metrics
        items={[
          ["知识文档", docs.length],
          ["隔离文档", docs.filter((d) => d.quarantined).length],
          ["检索融合", "BM25 + RRF"],
        ]}
      />
      <ErrorBox error={error} />
      <div className="columns">
        <div>
          <Card title="检索实验" kicker="01 / RETRIEVE">
            <div className="samples">
              <button
                disabled={busy}
                onClick={() =>
                  action(async () => {
                    await api("/seed", {});
                    await refresh();
                  })
                }
              >
                载入演示知识库
              </button>
              <button onClick={() => setQuery("Atlas 的对话数据保留多久？")}>
                数据保留
              </button>
              <button
                onClick={() => setQuery("How do agent approvals expire?")}
              >
                Agent 权限
              </button>
              <button onClick={() => setQuery("火星火山地质勘探")}>
                证据不足
              </button>
            </div>
            <label htmlFor="question">研究问题</label>
            <textarea
              id="question"
              rows={4}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <label htmlFor="mode">回答模式</label>
            <select
              id="mode"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
            >
              <option value="extractive">
                Extractive · 无需模型的原文证据
              </option>
              <option value="ollama">Ollama · 本地模型选择引用</option>
            </select>
            <button
              className="primary"
              disabled={busy || !query.trim()}
              onClick={() =>
                action(async () =>
                  setResult(await api("/query", { query, mode, top_k: 4 })),
                )
              }
            >
              <BookOpen size={16} />
              {busy ? "正在执行…" : "检索并验证引用"}
              <ArrowRight size={16} />
            </button>
            <p className="note">
              Ollama 模式需要服务端配置
              OLLAMA_MODEL。引用完整性校验不等于事实正确性或语义蕴含验证。
            </p>
          </Card>
          <Card title="导入知识" kicker="CONTENT-ADDRESSED">
            <label htmlFor="doc-title">文档标题</label>
            <input
              id="doc-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <label htmlFor="doc-content">文档正文</label>
            <textarea
              id="doc-content"
              rows={4}
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
            <button
              className="primary"
              disabled={busy || !title || content.length < 10}
              onClick={() =>
                action(async () => {
                  await api("/documents", { title, content });
                  setTitle("");
                  setContent("");
                  await refresh();
                })
              }
            >
              导入并检查
            </button>
          </Card>
        </div>
        <div>
          <Card title="回答与来源" kicker="02 / VERIFY">
            {result ? (
              <>
                <Badge good={result.status === "supported"}>
                  {result.status.toUpperCase()}
                </Badge>
                <p className="answer">{result.answer}</p>
                {result.matches.map((m: any) => (
                  <div className="signal" key={m.id}>
                    <h3>{m.title}</h3>
                    <p>{m.text}</p>
                    <code>
                      RRF {m.rrf_score} · 词项覆盖{" "}
                      {(m.query_coverage * 100).toFixed(0)}%
                    </code>
                  </div>
                ))}
                <Json value={result} />
              </>
            ) : (
              <Empty text="先载入知识库，再检索一个问题。" />
            )}
          </Card>
          <Card title="文档证据目录" kicker="PROVENANCE">
            {!docs.length ? (
              <p className="note">知识库为空。使用左侧按钮载入合成演示数据。</p>
            ) : (
              docs.map((d) => (
                <div className="signal" key={d.id}>
                  <h3>{d.title}</h3>
                  <div className="row">
                    <Badge good={!d.quarantined}>
                      {d.quarantined ? "QUARANTINED" : d.chunks + " CHUNKS"}
                    </Badge>
                    <button
                      disabled={busy}
                      onClick={() =>
                        action(async () => {
                          await api("/documents/" + d.id, undefined, "DELETE");
                          await refresh();
                        })
                      }
                    >
                      删除
                    </button>
                  </div>
                  <code>SHA256 {d.sha256.slice(0, 24)}…</code>
                </div>
              ))
            )}
          </Card>
        </div>
      </div>
    </Shell>
  );
}
