# University Academic Policy Assistant (LangGraph RAG)

A chat assistant that answers student questions on attendance, project submission, examinations,
lab safety/assessment and re-evaluation **only from indexed policy documents**. It decides per question
whether to **answer with citations, ask one clarification, or escalate** to the right office.

It runs fully offline: retrieval is a built-in BM25 index and the workflow nodes are deterministic,
so every answer is repeatable and every claim traces back to a policy section. No API key is needed.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m policy_assistant.cli --debug     # terminal chat (shows graph path, sources, timing)
streamlit run app.py                       # optional web chat UI
python eval/run_eval.py                    # 17 repeatable questions -> eval/report.md + results.json
pytest -q                                  # automated tests
python -m policy_assistant.cli --graph     # print the workflow as a Mermaid diagram
```

## Workflow (LangGraph)

```
START -> interpret -> retrieve -> grade --+--> answer    (cited answer / update note / competing refs)
                                          +--> clarify   (one focused question)
                                          +--> escalate  (out of scope or not in policy)
```

| Node | What it does |
|---|---|
| `interpret` | Detects topic, details the answer may depend on ("facets": project type, assessment category), intent (how-to / personal / action request). Merges a clarification reply into the original question. |
| `retrieve` | BM25 over section-level chunks, topic boost, step-section boost for "how do I..." questions. |
| `grade` | Checks the evidence: minimum score, IDF-weighted term coverage, facet conflicts. Decides `answer`, `clarify`, `competing` or `insufficient`. |
| `answer` | Resolves superseding circulars (newest applicable wins), quotes sections, adds update note, caveats and numbered citations. |
| `clarify` | Asks exactly one question and stores the pending state so the student only replies with the missing detail. |
| `escalate` | Abstains and names the relevant office. Lists the closest documents checked without claiming they answer. |

## Requirement coverage

| # | Requirement | Where |
|---|---|---|
| 01 | 8-12 documents with title and issue date metadata | `data/policies/` (10 docs); `ingest.py` also reads `.pdf` |
| 02 | Student-friendly answers | sections are written in plain language and quoted with their conditions |
| 03 | LangGraph flow with distinct stages | `graph.py`, `nodes.py` |
| 04 | One focused clarification, then continue | `interpret` + `clarify`; try *"project report deadline?"* then *"final year"* |
| 05 | Updates and competing references | `[updates=DOC#SECTION]` tags; `latest_version()`; `competing` verdict when applicability stays unclear |
| 06 | Citations and abstention | numbered sources with title, doc id, issue date, section (and page for PDFs); `escalate` node |
| 07 | Guided navigation without simulating | steps/forms shown only if the policy lists them; assistant refuses to "submit" and never confirms eligibility |
| 08 | Evaluation and observability | `eval/run_eval.py`: path, retrieved sources, answer type, per-node and total time, citation/retrieval metrics |
| 09 | Chat UX and tests | `cli.py`, `app.py`, `tests/test_assistant.py` |

## Adding or updating policies

Drop a `.txt`, `.md` or text-layer `.pdf` into `data/policies/`:

```
TITLE: Attendance Requirements Policy
DOC_ID: ATT-2023-01
ISSUED: 2023-07-10
CATEGORY: attendance

SECTION 3 [project_type=final; updates=PRJ-2023-02#3]: Heading
Plain-language rule text...
```

* `[key=value]` tags mark sections that only apply to one case. If retrieved sections disagree on that key and the
  student has not said which applies, the assistant asks.
* `updates=DOC#SECTION` marks a circular section as superseding an older one (the newer `ISSUED` date wins, and only if
  its own facets match the student's situation).
* New topics: add keywords to `CATEGORY_PATTERNS`, new clarification dimensions to `FACETS`/`FACET_PROMPTS`
  and the office to `OFFICES` in `policy_assistant/config.py`.

## Notes and limits

* The 10 policy documents are **synthetic samples** written for this project - replace them with real circulars.
* Retrieval is lexical (BM25 + light stemming). To use embeddings or an LLM for wording, swap the body of
  `BM25Retriever.search` or post-process the text built in the `answer` node; the graph and tests stay the same.
* Thresholds (`MIN_SCORE`, `MIN_COVERAGE`, `REL_RATIO`, `ANSWER_RATIO`) live in `config.py` and were tuned on the
  sample corpus; re-run `python eval/run_eval.py` after changing documents or thresholds.
