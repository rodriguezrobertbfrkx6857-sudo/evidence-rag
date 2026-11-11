"""Local hybrid retrieval: BM25 + character trigram cosine, fused with RRF."""

import hashlib
import math
import re
import unicodedata
from collections import Counter

from app.platform import database


def tokens(text):
    text = unicodedata.normalize("NFKC", text).lower()
    words = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text)
    return words + [
        text[i : i + 2]
        for i in range(len(text) - 1)
        if all("\u4e00" <= c <= "\u9fff" for c in text[i : i + 2])
    ]


def grams(text):
    text = " ".join(tokens(text))
    return Counter(text[i : i + 3] for i in range(max(0, len(text) - 2)))


def quarantine(text):
    normalized = "".join(
        c for c in unicodedata.normalize("NFKC", text) if unicodedata.category(c) != "Cf"
    ).lower()
    patterns = [
        r"ignore.{0,20}(?:instructions|rules)",
        r"(?:reveal|send|print).{0,30}(?:system prompt|secret|password)",
        r"忽略.{0,10}(?:指令|规则)",
        r"输出.{0,10}(?:系统提示|密钥)",
        r"\[system\]|<\|im_start\|>",
    ]
    return any(re.search(p, normalized, re.DOTALL) for p in patterns)


def connect():
    db = database()
    db.execute(
        "CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,title TEXT,content TEXT,sha256 TEXT,quarantined INTEGER)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY,document_id TEXT,ordinal INTEGER,text TEXT)"
    )
    return db


def ingest(title, content):
    digest = hashlib.sha256(content.encode()).hexdigest()
    docid = hashlib.sha256((title + "\0" + content).encode()).hexdigest()[:24]
    # Paragraph-aware bounded windows; overlap preserves evidence across long paragraphs.
    pieces = []
    for paragraph in re.split(r"\n\s*\n", content):
        if paragraph.strip():
            for start in range(0, len(paragraph), 600):
                pieces.append(paragraph[start : start + 800].strip())
    blocked = quarantine(content)
    with connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO documents VALUES(?,?,?,?,?)", (docid, title, content, digest, blocked)
        )
        for index, piece in enumerate(pieces):
            db.execute(
                "INSERT OR IGNORE INTO chunks VALUES(?,?,?,?)", (f"{docid}:{index}", docid, index, piece)
            )
    return {"id": docid, "title": title, "sha256": digest, "quarantined": blocked, "chunks": len(pieces)}


def documents():
    with connect() as db:
        return [
            dict(r)
            for r in db.execute(
                "SELECT id,title,sha256,quarantined,(SELECT COUNT(*) FROM chunks WHERE document_id=documents.id) AS chunks FROM documents ORDER BY title"
            )
        ]


def retrieve(query, k=4):
    with connect() as db:
        rows = [
            dict(r)
            for r in db.execute(
                "SELECT c.*,d.title,d.sha256 FROM chunks c JOIN documents d ON d.id=c.document_id WHERE d.quarantined=0 ORDER BY c.id"
            )
        ]
    if not rows:
        return []
    counters = [Counter(tokens(r["text"])) for r in rows]
    q = Counter(tokens(query))
    qg = grams(query)
    lengths = [sum(c.values()) for c in counters]
    avg = sum(lengths) / len(rows) or 1
    scores = []
    for index, (row, count) in enumerate(zip(rows, counters)):
        bm25 = 0
        for word in q:
            df = sum(word in c for c in counters)
            tf = count[word]
            bm25 += (
                math.log(1 + (len(rows) - df + 0.5) / (df + 0.5))
                * tf
                * 2.5
                / (tf + 1.5 * (0.25 + 0.75 * lengths[index] / avg))
            )
        cg = grams(row["text"])
        denom = math.sqrt(sum(v * v for v in qg.values()) * sum(v * v for v in cg.values()))
        cosine = sum(v * cg[t] for t, v in qg.items()) / denom if denom else 0
        scores.append((index, bm25, cosine))
    fused = {i: 0.0 for i in range(len(rows))}
    for axis in (1, 2):
        rank = 0
        for item in sorted(scores, key=lambda t: (-t[axis], t[0])):
            if item[axis] <= 0:
                continue
            rank += 1
            fused[item[0]] += 1 / (60 + rank)
    matches = []
    for index in sorted(fused, key=lambda i: (-fused[i], i)):
        overlap = len(set(q) & set(counters[index])) / max(1, len(q))
        # Reject weak trigram-only matches; this is lexical coverage, not a confidence probability.
        if overlap < 0.15:
            continue
        matches.append(
            {
                **rows[index],
                "rrf_score": round(fused[index], 6),
                "query_coverage": round(overlap, 3),
                "bm25": round(scores[index][1], 4),
                "trigram_cosine": round(scores[index][2], 4),
            }
        )
    return matches[:k]


def verify_quotes(quotes, chunks):
    allowed = {c["id"]: c for c in chunks}
    if not quotes:
        return False
    for quote in quotes:
        if not isinstance(quote, dict) or set(quote) != {"chunk_id", "quote"}:
            return False
        if not isinstance(quote.get("chunk_id"), str):
            return False
        chunk = allowed.get(quote.get("chunk_id"))
        value = quote.get("quote")
        if not chunk or not isinstance(value, str) or len(value.strip()) < 5 or value not in chunk["text"]:
            return False
    return True
