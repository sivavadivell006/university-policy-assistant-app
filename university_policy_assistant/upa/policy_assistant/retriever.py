"""Small, dependency-free BM25 retriever over policy sections."""
from __future__ import annotations

import math
from collections import Counter

import re

from .config import CATEGORY_BOOST, COVERAGE_IGNORE, STEP_BOOST, STEP_PENALTY
from .ingest import Chunk
from .textutils import tokenize


class BM25Retriever:
    def __init__(self, chunks: list[Chunk], k1: float = 1.4, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.tf = [Counter(c.tokens()) for c in chunks]
        self.len = [sum(t.values()) for t in self.tf]
        self.avgdl = sum(self.len) / len(self.len)
        self.df: Counter = Counter()
        for t in self.tf:
            self.df.update(t.keys())
        self.n = len(chunks)

    def idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query: str, k: int = 6, categories: set | None = None, process: bool = False) -> list[tuple[Chunk, float]]:
        q = tokenize(query)
        scored = []
        for i, chunk in enumerate(self.chunks):
            s = 0.0
            for term in set(q):
                f = self.tf[i].get(term, 0)
                if f:
                    s += self.idf(term) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avgdl))
            if s > 0 and categories and chunk.category in categories:
                s *= CATEGORY_BOOST
            if s > 0:
                has_steps = bool(re.search(r"^\s*1\.", chunk.body, re.M))
                if has_steps:
                    s *= STEP_BOOST if process else STEP_PENALTY
                scored.append((chunk, s))
        scored.sort(key=lambda x: (-x[1], x[0].id))
        return scored[:k]

    def coverage(self, query: str, chunks: list[Chunk]) -> float:
        """IDF-weighted share of question terms that appear in the given evidence.
        Terms never seen in the corpus get the highest weight, so off-topic
        questions score near zero."""
        ignore = {t for w in COVERAGE_IGNORE for t in tokenize(w)}
        q = {t for t in tokenize(query) if not t.isdigit() and t not in ignore}
        if not q:
            return 1.0
        have = set()
        for c in chunks:
            have.update(c.tokens())
        total = sum(self.idf(t) for t in q)
        return sum(self.idf(t) for t in q if t in have) / total if total else 0.0
