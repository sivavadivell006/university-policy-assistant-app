"""Terminal chat:  python -m policy_assistant.cli  [--debug] [--graph]"""
import argparse

from .assistant import PolicyAssistant


def main() -> None:
    ap = argparse.ArgumentParser(description="University Academic Policy Assistant")
    ap.add_argument("--debug", action="store_true", help="show graph path, retrieved sources and timing")
    ap.add_argument("--graph", action="store_true", help="print the workflow as a Mermaid diagram and exit")
    args = ap.parse_args()
    bot = PolicyAssistant()

    if args.graph:
        print(bot.graph.get_graph().draw_mermaid())
        return

    print("University Academic Policy Assistant  (type 'docs' to list policies, 'new' to reset, 'quit' to exit)\n")
    while True:
        try:
            q = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q.lower() in {"quit", "exit", "q"}:
            break
        if q.lower() == "new":
            bot.reset()
            print("Assistant: Started a new conversation.\n")
            continue
        if q.lower() == "docs":
            for d in bot.documents:
                print(f"  {d['doc_id']:<12} {d['issued']}  {d['title']}")
            print()
            continue
        r = bot.ask(q)
        print(f"\nAssistant: {r['answer']}\n")
        if args.debug:
            print(f"  [path: {' -> '.join(r['path'])} | type: {r['answer_subtype']} | "
                  f"retrieved: {', '.join(x['id'] for x in r['retrieved'][:4])} | {r['elapsed_ms']} ms]\n")


if __name__ == "__main__":
    main()
