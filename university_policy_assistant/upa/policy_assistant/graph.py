"""Build the LangGraph workflow."""
from langgraph.graph import END, START, StateGraph

from .ingest import Chunk
from .nodes import State, make_nodes
from .retriever import BM25Retriever


def build_graph(corpus: list[Chunk], retriever: BM25Retriever):
    n = make_nodes(corpus, retriever)
    g = StateGraph(State)
    for name in ("interpret", "retrieve", "grade", "answer", "clarify", "escalate"):
        g.add_node(name, n[name])
    g.add_edge(START, "interpret")
    g.add_edge("interpret", "retrieve")
    g.add_edge("retrieve", "grade")
    g.add_conditional_edges("grade", n["route"], {"answer": "answer", "clarify": "clarify", "escalate": "escalate"})
    for terminal in ("answer", "clarify", "escalate"):
        g.add_edge(terminal, END)
    return g.compile()
