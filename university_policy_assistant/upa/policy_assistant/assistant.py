"""Chat session wrapper around the compiled graph (holds clarification state)."""
from __future__ import annotations

import time
from pathlib import Path

from .config import POLICY_DIR
from .graph import build_graph
from .ingest import load_corpus
from .retriever import BM25Retriever


class PolicyAssistant:
    def __init__(self, policy_dir: Path = POLICY_DIR):
        self.corpus = load_corpus(policy_dir)
        self.retriever = BM25Retriever(self.corpus)
        self.graph = build_graph(self.corpus, self.retriever)
        self.pending: dict | None = None

    @property
    def documents(self) -> list[dict]:
        seen = {}
        for c in self.corpus:
            seen.setdefault(c.doc_id, {"doc_id": c.doc_id, "title": c.title, "issued": c.issued.isoformat(),
                                       "category": c.category})
        return sorted(seen.values(), key=lambda d: d["doc_id"])

    def reset(self) -> None:
        self.pending = None

    def ask(self, question: str) -> dict:
        t0 = time.perf_counter()
        out = self.graph.invoke({"question": question, "pending": self.pending, "path": [], "timings": {}})
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        self.pending = out.get("pending_out")
        return {
            "question": question,
            "answer": out["answer"],
            "answer_type": out["answer_type"],
            "answer_subtype": out["answer_subtype"],
            "path": out["path"],
            "cited": out["cited"],
            "retrieved": [{"id": c.id, "score": round(s, 3)} for c, s in out.get("hits", [])],
            "verdict": out.get("verdict"),
            "reason": out.get("reason"),
            "coverage": out.get("coverage"),
            "timings_ms": out["timings"],
            "elapsed_ms": elapsed,
        }
