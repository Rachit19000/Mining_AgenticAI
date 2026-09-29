"""CLI chat interface for the MineOps Agent.

Usage:
    python main.py                 # interactive chat
    python main.py "Is Zone B safe?"   # single question
    python main.py --demo          # run the built-in example questions
"""

import sys

from agent.agent import ask

DEMO_QUESTIONS = [
    "Is Zone B safe for workers right now?",
    "Which equipment needs urgent maintenance?",
    "Are there safety risks from the last shift?",
    "Which zone should be inspected first?",
    "What should the supervisor do about the methane alert in Zone B?",
]


def render(response):
    print("=" * 70)
    print(f"Q: {response['question']}")
    print("-" * 70)
    print(f"Intent: {response['intent']}")
    print("Plan:")
    for i, step in enumerate(response["plan"], 1):
        print(f"  {i}. {step}")
    print("Tool calls:")
    print(response["tool_log"])
    print("-" * 70)
    print(response["answer"])
    print(f"\nConfidence: {response['confidence']}")
    print("=" * 70)
    print()


def run_demo():
    for q in DEMO_QUESTIONS:
        render(ask(q))


def interactive():
    print("MineOps Agent. Ask a question (type 'exit' to quit, 'demo' for examples).")
    while True:
        try:
            q = input("\nSupervisor> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q.lower() in ("exit", "quit"):
            break
        if q.lower() == "demo":
            run_demo()
            continue
        render(ask(q))


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--demo":
        run_demo()
    elif args:
        render(ask(" ".join(args)))
    else:
        interactive()
