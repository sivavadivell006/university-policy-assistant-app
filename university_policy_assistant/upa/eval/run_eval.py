"""Run the repeatable evaluation set and write eval/results.json + eval/report.md.

    python eval/run_eval.py [--repeat 3]
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from policy_assistant import PolicyAssistant  # noqa: E402


def run_case(bot: PolicyAssistant, case: dict) -> dict:
    bot.reset()
    turns = [bot.ask(t) for t in case["turns"]]
    final, exp = turns[-1], case["expect"]
    cited, required = set(final["cited"]), set(exp["cited"])
    allowed = required | set(exp.get("acceptable", []))
    retrieved_ids = [r["id"] for r in final["retrieved"]]
    checks = {
        "answer_type": final["answer_type"] == exp["answer_type"],
        "subtype": exp.get("subtype", final["answer_subtype"]) == final["answer_subtype"],
        "path": final["path"] == exp["path"],
        "required_cited": required <= cited,
        "no_stale_citation": not (cited & set(exp.get("must_not_cite", []))),
        "phrases": all(p.lower() in final["answer"].lower() for p in exp.get("phrases", [])),
    }
    return {
        "id": case["id"], "tag": case["tag"], "turns": case["turns"],
        "path_per_turn": [t["path"] for t in turns],
        "answer_type": final["answer_type"], "subtype": final["answer_subtype"],
        "retrieved": retrieved_ids, "cited": final["cited"],
        "retrieval_hit": required <= set(retrieved_ids) if required else None,
        "citation_precision": (len(cited & allowed) / len(cited)) if cited else None,
        "citation_recall": (len(cited & required) / len(required)) if required else None,
        "elapsed_ms": round(sum(t["elapsed_ms"] for t in turns), 2),
        "node_timings_ms": final["timings_ms"],
        "checks": checks, "passed": all(checks.values()), "answer": final["answer"],
    }


def avg(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 3) if xs else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=3, help="runs per question to verify repeatability")
    args = ap.parse_args()

    cases = json.loads((ROOT / "eval" / "questions.json").read_text())
    bot = PolicyAssistant()
    results, deterministic = [], True
    for case in cases:
        runs = [run_case(bot, case) for _ in range(args.repeat)]
        if len({r["answer"] for r in runs}) > 1 or len({tuple(r["cited"]) for r in runs}) > 1:
            deterministic = False
        res = runs[0]
        res["elapsed_ms"] = round(statistics.median(r["elapsed_ms"] for r in runs), 2)
        results.append(res)

    n = len(results)
    update_cases = [r for r in results if r["tag"] in {"policy_update", "ambiguity+update", "guided_process"}]
    summary = {
        "questions": n,
        "passed": sum(r["passed"] for r in results),
        "answer_type_accuracy": avg([r["checks"]["answer_type"] and r["checks"]["subtype"] for r in results]),
        "path_accuracy": avg([r["checks"]["path"] for r in results]),
        "retrieval_hit_rate": avg([r["retrieval_hit"] for r in results]),
        "citation_recall": avg([r["citation_recall"] for r in results]),
        "citation_precision": avg([r["citation_precision"] for r in results]),
        "latest_circular_correct": avg([r["checks"]["required_cited"] and r["checks"]["no_stale_citation"] for r in update_cases]),
        "repeatable_across_runs": deterministic,
        "median_latency_ms": round(statistics.median(r["elapsed_ms"] for r in results), 2),
        "max_latency_ms": max(r["elapsed_ms"] for r in results),
    }
    (ROOT / "eval" / "results.json").write_text(json.dumps({"summary": summary, "results": results}, indent=2))

    lines = ["# Evaluation report", "", "## Summary", "", "| Metric | Value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in summary.items()]
    lines += ["", "## Per-question results", "",
              "| ID | Tag | Graph path (final turn) | Answer type | Retrieved (top 4) | Cited | ms | Pass |", "|---|---|---|---|---|---|---|---|"]
    for r in results:
        path = " > ".join(r["path_per_turn"][-1])
        lines.append(f"| {r['id']} | {r['tag']} | {path} | {r['subtype']} | {', '.join(r['retrieved'][:4]) or '-'} | "
                     f"{', '.join(r['cited']) or '-'} | {r['elapsed_ms']} | {'PASS' if r['passed'] else 'FAIL'} |")
    failed = [r for r in results if not r["passed"]]
    if failed:
        lines += ["", "## Failures", ""]
        for r in failed:
            lines.append(f"- **{r['id']}**: failed checks -> {[k for k, v in r['checks'].items() if not v]}")
    (ROOT / "eval" / "report.md").write_text("\n".join(lines) + "\n")

    print("\n".join(lines))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
