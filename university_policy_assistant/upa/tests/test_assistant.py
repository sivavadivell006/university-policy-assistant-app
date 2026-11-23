"""Automated tests for the four required paths plus supporting behaviour.

    pytest -q
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from policy_assistant import PolicyAssistant  # noqa: E402
from policy_assistant.ingest import load_corpus, parse_document  # noqa: E402

ANSWER_PATH = ["interpret", "retrieve", "grade", "answer"]


@pytest.fixture()
def bot():
    return PolicyAssistant()


# ---------------------------------------------------------------- corpus
def test_corpus_has_8_to_12_documents_with_metadata(bot):
    docs = bot.documents
    assert 8 <= len(docs) <= 12
    assert all(d["title"] and d["issued"] and d["doc_id"] for d in docs)


# ---------------------------------------------------------- answer path
def test_answer_path_cites_title_section_and_date(bot):
    r = bot.ask("What is the minimum attendance I need to write the end-semester exam?")
    assert r["path"] == ANSWER_PATH
    assert r["answer_type"] == "answer"
    assert "75%" in r["answer"]
    assert "Attendance Requirements Policy" in r["answer"] and "Section 1" in r["answer"] and "10 Jul 2023" in r["answer"]
    assert r["cited"] == ["ATT-2023-01#1"]


# ---------------------------------------------------- clarification path
def test_clarification_path_asks_one_focused_question(bot):
    r = bot.ask("What is the project report submission deadline?")
    assert r["path"] == ["interpret", "retrieve", "grade", "clarify"]
    assert r["answer_type"] == "clarification"
    assert r["answer"].count("?") == 1
    assert bot.pending["facet"] == "project_type"


def test_clarification_reply_continues_without_repeating_question(bot):
    bot.ask("What is the project report submission deadline?")
    r = bot.ask("final year")                       # short reply only
    assert r["answer_type"] == "answer"
    assert "15 working days" in r["answer"]
    assert bot.pending is None


def test_unresolved_clarification_shows_competing_references(bot):
    bot.ask("What is the project report submission deadline?")
    r = bot.ask("not sure")
    assert r["answer_subtype"] == "competing_references"
    assert {"PRJ-2023-02#2", "PRJ-2025-04#1"} <= set(r["cited"])
    assert "rather than guessing" in r["answer"]


def test_new_question_after_clarification_is_not_swallowed(bot):
    bot.ask("What is the project report submission deadline?")
    r = bot.ask("What should I do if there is a fire in the lab?")
    assert r["answer_type"] == "answer" and "LAB-2023-05#4" in r["cited"]


# ----------------------------------------------- insufficient-evidence path
def test_insufficient_evidence_abstains_and_points_to_office(bot):
    r = bot.ask("What is the grace marks policy for failed papers?")
    assert r["path"] == ["interpret", "retrieve", "grade", "escalate"]
    assert r["answer_type"] == "escalation" and r["answer_subtype"] == "insufficient_evidence"
    assert r["cited"] == []
    assert "Controller of Examinations" in r["answer"]


def test_out_of_scope_question_is_escalated(bot):
    r = bot.ask("What is the weather in Chennai today?")
    assert r["answer_subtype"] == "out_of_scope" and r["cited"] == []


# ------------------------------------------------ latest circular is used
def test_latest_circular_replaces_older_rule_and_mentions_update(bot):
    r = bot.ask("How much is the re-evaluation fee?")
    assert "REV-2025-02#1" in r["cited"] and "REV-2023-07#2" not in r["cited"]
    assert "Rs. 1500" in r["answer"]
    assert "more recent circular REV-2025-02" in r["answer"]


def test_attendance_condonation_uses_2024_circular(bot):
    r = bot.ask("Can I get attendance condonation and what is the fee?")
    assert r["answer_subtype"] == "answer_with_update"
    assert "ATT-2024-03#1" in r["cited"] and "ATT-2023-01#3" not in r["cited"]
    assert "Rs. 500" in r["answer"] and "70%" in r["answer"]


def test_facet_selects_latest_applicable_circular_only(bot):
    mini = bot.ask("When do I submit my mini project report?")
    assert "PRJ-2023-02#2" in mini["cited"] and "PRJ-2025-04#1" not in mini["cited"]
    final = bot.ask("When do I submit my final year project report?")
    assert "PRJ-2025-04#1" in final["cited"] and "PRJ-2023-02#3" not in final["cited"]


# ----------------------------------------------------- guided navigation
def test_guided_steps_come_from_policy_only(bot):
    r = bot.ask("How do I apply for re-evaluation?")
    assert "RE-01" in r["answer"] and "1. Optionally request a photocopy" in r["answer"]


def test_assistant_never_pretends_to_submit_or_confirm_eligibility(bot):
    r = bot.ask("Please submit my re-evaluation request for me")
    assert "cannot submit or file requests" in r["answer"]
    r = bot.ask("My attendance is 68%. Am I eligible for condonation?")
    assert "cannot confirm that you are eligible" in r["answer"]


# --------------------------------------------------------- observability
def test_every_turn_records_path_sources_type_and_time(bot):
    r = bot.ask("Can I carry my mobile phone into the exam hall if it is switched off?")
    assert r["path"] and r["retrieved"] and r["answer_type"] and r["elapsed_ms"] >= 0
    assert set(r["timings_ms"]) == set(r["path"])


# --------------------------------------------------------------- ingestion
def test_parser_rejects_documents_without_metadata():
    with pytest.raises(ValueError):
        parse_document("SECTION 1: Heading\nbody")


def test_pdf_ingestion_keeps_metadata_and_page_numbers(tmp_path):
    reportlab = pytest.importorskip("reportlab")
    pytest.importorskip("pypdf")
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(tmp_path / "sample.pdf"), pagesize=A4)
    page1 = ["TITLE: Sample Policy", "DOC_ID: SMP-2025-01", "ISSUED: 2025-05-01", "CATEGORY: attendance", "",
             "SECTION 1: First rule", "Students must do the first thing."]
    page2 = ["SECTION 2: Second rule", "Students must do the second thing."]
    for lines in (page1, page2):
        y = 800
        for line in lines:
            pdf.drawString(50, y, line)
            y -= 18
        pdf.showPage()
    pdf.save()
    chunks = load_corpus(tmp_path)
    assert [c.id for c in chunks] == ["SMP-2025-01#1", "SMP-2025-01#2"]
    assert chunks[0].page == 1 and chunks[1].page == 2 and chunks[0].title == "Sample Policy"
    assert "p. 2" in chunks[1].citation()


# ------------------------------------------------------- evaluation set
def test_full_evaluation_set_passes():
    sys.path.insert(0, str(ROOT / "eval"))
    import run_eval

    bot = PolicyAssistant()
    cases = json.loads((ROOT / "eval" / "questions.json").read_text())
    assert len(cases) >= 8
    failed = [c["id"] for c in cases if not run_eval.run_case(bot, c)["passed"]]
    assert not failed, f"failed eval cases: {failed}"
