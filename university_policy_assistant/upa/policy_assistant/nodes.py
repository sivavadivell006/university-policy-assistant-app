"""LangGraph nodes: interpret -> retrieve -> grade -> (answer | clarify | escalate)."""
from __future__ import annotations

import re
import time
from functools import wraps
from typing import Callable, TypedDict

from . import config
from .ingest import Chunk
from .retriever import BM25Retriever
from .textutils import tokenize


class State(TypedDict, total=False):
    # input
    question: str
    pending: dict | None            # clarification awaiting a reply (from previous turn)
    # interpret
    effective_question: str
    categories: set
    facets: dict
    intent: dict
    already_clarified: bool
    clarification_unresolved: bool
    # retrieve
    hits: list                      # [(Chunk, score)]
    # grade
    verdict: str                    # answer | competing | clarify | insufficient
    reason: str
    relevant: list
    clarify_facet: str | None
    coverage: float
    # outputs
    answer: str
    answer_type: str                # answer | clarification | escalation
    answer_subtype: str
    cited: list
    pending_out: dict | None
    # observability
    path: list
    timings: dict


# ---------------------------------------------------------------- helpers
def traced(name: str):
    """Record the node in the execution path and time it."""
    def deco(fn: Callable):
        @wraps(fn)
        def wrapper(state: State) -> dict:
            t0 = time.perf_counter()
            out = fn(state)
            ms = round((time.perf_counter() - t0) * 1000, 2)
            out["path"] = list(state.get("path", [])) + [name]
            out["timings"] = {**state.get("timings", {}), name: ms}
            return out
        return wrapper
    return deco


def detect_categories(text: str) -> set:
    t = text.lower()
    t = re.sub(r"re[\s-]?evaluation|re[\s-]?valuation|revaluation", "reevaluation", t)
    return {c for c, pat in config.CATEGORY_PATTERNS.items() if re.search(pat, t)}


def detect_facets(text: str) -> dict:
    t = text.lower()
    found = {}
    for facet, values in config.FACETS.items():
        hits = [v for v, pat in values.items() if re.search(pat, t)]
        if len(hits) == 1:           # conflicting signals => leave undecided
            found[facet] = hits[0]
    return found


def detect_intent(text: str) -> dict:
    t = text.lower()
    return {
        "process": bool(re.search(r"\bhow (do|can|should|to)\b|\bsteps?\b|procedure|process|\bapply\b|how to", t)),
        "personal": bool(re.search(r"\bam i\b|\bmy (attendance|marks|result|score|cgpa|percentage|record)|eligible|qualify", t)),
        "action": bool(re.search(r"for me\b|on my behalf|\bsubmit my\b|\bfile my\b|\braise my\b", t)),
    }


def office_for(categories: set, hits: list) -> str:
    top = hits[0][0].category if hits else None
    cat = top if top in categories else (sorted(categories)[0] if categories else top)
    return config.OFFICES.get(cat, config.OFFICES[None])


# ------------------------------------------------------------------ nodes
def make_nodes(corpus: list[Chunk], retriever: BM25Retriever):
    by_id = {c.id: c for c in corpus}
    updated_by: dict[str, list[Chunk]] = {}
    for c in corpus:
        for ref in c.updates:
            updated_by.setdefault(ref, []).append(c)

    def latest_version(chunk: Chunk, facets: dict) -> Chunk:
        """Follow 'updates' links to the newest circular that applies to the student's facets."""
        current = chunk
        while True:
            candidates = [
                u for u in updated_by.get(current.id, [])
                if u.issued > current.issued
                and all(facets.get(k, v) == v for k, v in u.facets.items())
            ]
            if not candidates:
                return current
            current = max(candidates, key=lambda u: u.issued)

    # 1 ------------------------------------------------------------ interpret
    @traced("interpret")
    def interpret(state: State) -> dict:
        q = state["question"].strip()
        pending = state.get("pending")
        effective, unresolved, clarified = q, False, False
        if pending:
            reply_facets = detect_facets(q)
            if pending["facet"] in reply_facets:        # reply answers the clarification
                # merge the reply into the original question: the student need not repeat it
                effective, clarified = f"{pending['question']} {q}", True
                facets = detect_facets(effective)
            elif len(tokenize(q)) <= 4 and not detect_categories(q):   # reply did not help
                effective, clarified, unresolved = pending["question"], True, True
                facets = detect_facets(effective)
            else:                                        # student moved on to a new question
                facets = detect_facets(effective)
        else:
            facets = detect_facets(effective)
        return {
            "effective_question": effective,
            "categories": detect_categories(effective),
            "facets": facets,
            "intent": detect_intent(effective),
            "already_clarified": clarified,
            "clarification_unresolved": unresolved,
        }

    # 2 ------------------------------------------------------------ retrieve
    @traced("retrieve")
    def retrieve(state: State) -> dict:
        hits = retriever.search(state["effective_question"], k=config.TOP_K, categories=state["categories"],
                                process=state["intent"]["process"])
        return {"hits": hits}

    # 3 ---------------------------------------------------------------- grade
    @traced("grade")
    def grade(state: State) -> dict:
        hits, facets = state["hits"], dict(state["facets"])
        q = state["effective_question"]
        if not hits or hits[0][1] < config.MIN_SCORE:
            return {"verdict": "insufficient", "reason": "out_of_scope" if not state["categories"] else "not_in_policy",
                    "coverage": 0.0, "relevant": []}
        coverage = retriever.coverage(q, [c for c, _ in hits[:3]])
        if coverage < config.MIN_COVERAGE:
            return {"verdict": "insufficient", "reason": "out_of_scope" if not state["categories"] else "not_in_policy",
                    "coverage": round(coverage, 2), "relevant": []}

        top = hits[0][1]
        relevant = [(c, s) for c, s in hits if s >= config.REL_RATIO * top][: config.TOP_K]
        # drop sections whose facet conflicts with what the student told us
        relevant = [(c, s) for c, s in relevant if all(facets.get(k, v) == v for k, v in c.facets.items())]
        if not relevant:
            return {"verdict": "insufficient", "reason": "not_in_policy", "coverage": round(coverage, 2), "relevant": []}

        # does the answer depend on a detail we do not have?
        ambiguous = []
        for facet in config.FACETS:
            if facet in facets:
                continue
            vals = {c.facets[facet] for c, _ in relevant if facet in c.facets}
            if len(vals) >= 2:
                ambiguous.append(facet)
        if ambiguous:
            if state.get("already_clarified"):
                return {"verdict": "competing", "reason": "ambiguity_unresolved", "clarify_facet": ambiguous[0],
                        "coverage": round(coverage, 2), "relevant": relevant}
            return {"verdict": "clarify", "reason": "ambiguous", "clarify_facet": ambiguous[0],
                    "coverage": round(coverage, 2), "relevant": relevant}
        return {"verdict": "answer", "reason": "supported", "coverage": round(coverage, 2), "relevant": relevant}

    # routing -------------------------------------------------------------
    def route(state: State) -> str:
        return {"answer": "answer", "competing": "answer", "clarify": "clarify", "insufficient": "escalate"}[state["verdict"]]

    # 4a -------------------------------------------------------------- answer
    @traced("answer")
    def answer(state: State) -> dict:
        intent, facets = state["intent"], state["facets"]
        relevant = state["relevant"]
        notes, subtype = [], "answer"

        if state["verdict"] == "competing":
            facet = state["clarify_facet"]
            groups: dict[str, tuple] = {}
            for c, s in relevant:
                if facet in c.facets:
                    val = c.facets[facet]
                    chosen = latest_version(c, {**facets, facet: val})
                    groups.setdefault(val, (chosen, c))
            evidence = [g[0] for g in groups.values()]
            subtype = "competing_references"
            body = ["I could not tell which case applies to you, so I am showing both rather than guessing:"]
            for i, (val, (chosen, _orig)) in enumerate(groups.items(), 1):
                label = val.replace("_", " ")
                body.append(f"\nIf this is about {label}: {chosen.body}  [{i}]")
            notes.append("Please confirm which applies to you with " + office_for(state["categories"], state["hits"]) + ".")
        else:
            evidence, seen = [], set()
            top_score = relevant[0][1]
            quote_ratio = config.REL_RATIO if intent["process"] else config.ANSWER_RATIO
            for c, s in relevant:
                if s < quote_ratio * top_score:
                    continue
                latest = latest_version(c, facets)
                if latest.id in seen:
                    continue
                seen.add(latest.id)
                evidence.append(latest)
            evidence = evidence[: config.MAX_EVIDENCE_PROCESS if intent["process"] else config.MAX_EVIDENCE]
            if any(c.updates for c in evidence):
                subtype = "answer_with_update"
            body = []
            for i, c in enumerate(evidence, 1):
                body.append(f"{c.heading} [{i}]\n{c.body}" if len(evidence) > 1 else f"{c.body}  [{i}]")
            body = ["\n\n".join(body)]
            for c in evidence:
                for ref in c.updates:
                    old = by_id.get(ref)
                    if old:
                        notes.append(
                            f"Update: this reflects the more recent circular {c.doc_id} (issued {c.issued_str}), "
                            f"which replaces Section {old.section} of the earlier {old.title} ({old.doc_id}, issued {old.issued_str})."
                        )
            if intent["process"] and not any(re.search(r"^\s*1\.", c.body, re.M) for c in evidence):
                notes.append("The policy documents I have do not list step-by-step instructions or forms for this; "
                             "please check with " + office_for(state["categories"], state["hits"]) + ".")
        if intent["action"]:
            notes.append("I can only explain the policy - I cannot submit or file requests on your behalf.")
        if intent["personal"]:
            notes.append("I cannot see your personal records, so I cannot confirm that you are eligible. "
                         "The rule above is what applies; confirm your case with " + office_for(state["categories"], state["hits"]) + ".")

        sources = "\n".join(f"[{i}] {c.citation()}" for i, c in enumerate(evidence, 1))
        text = "\n".join(body) + ("\n\n" + "\n".join(notes) if notes else "") + "\n\nSources:\n" + sources
        return {"answer": text, "answer_type": "answer", "answer_subtype": subtype,
                "cited": [c.id for c in evidence], "pending_out": None}

    # 4b ------------------------------------------------------------- clarify
    @traced("clarify")
    def clarify(state: State) -> dict:
        facet = state["clarify_facet"]
        text = "One quick question so I give you the right rule: " + config.FACET_PROMPTS[facet]
        return {"answer": text, "answer_type": "clarification", "answer_subtype": "clarification", "cited": [],
                "pending_out": {"question": state["effective_question"], "facet": facet}}

    # 4c ------------------------------------------------------------- escalate
    @traced("escalate")
    def escalate(state: State) -> dict:
        office = office_for(state["categories"], state["hits"])
        if state["reason"] == "out_of_scope":
            text = ("That question is outside the university policy documents I can search (attendance, project "
                    "submission, examinations, lab safety/assessment and re-evaluation). "
                    f"For anything else, please contact {office}.")
            subtype = "out_of_scope"
        else:
            text = ("I searched the policy documents but could not find a rule that answers this, and I do not want "
                    f"to guess. Please contact {office} for official confirmation.")
            if state["hits"]:
                seen = []
                for c, _ in state["hits"][:3]:
                    if c.title not in seen:
                        seen.append(c.title)
                text += "\n\nClosest documents I checked (they do not answer your question): " + "; ".join(seen) + "."
            subtype = "insufficient_evidence"
        return {"answer": text, "answer_type": "escalation", "answer_subtype": subtype, "cited": [], "pending_out": None}

    return {"interpret": interpret, "retrieve": retrieve, "grade": grade, "answer": answer,
            "clarify": clarify, "escalate": escalate, "route": route}
