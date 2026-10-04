import argparse

from market_assistant.agent import build_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Indian stock market paper-trading assistant")
    parser.add_argument("--client", default="C001", help="logged-in client id (C001 or C002)")
    parser.add_argument("--ask", help="ask a single question and exit")
    parser.add_argument("--quiet", action="store_true", help="hide the Thought/Action/Observation trace")
    args = parser.parse_args()

    agent = build_agent(client_id=args.client, verbose=not args.quiet)

    if args.ask:
        print(agent.run(args.ask).answer)
        return

    print(f"Market assistant for client {args.client}. Type 'exit' to quit.")
    history = []
    while True:
        try:
            goal = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if goal.lower() in ("exit", "quit"):
            break
        if not goal:
            continue
        result = agent.run(goal, history)
        print(f"\nAssistant: {result.answer}")
        history += result.turn


if __name__ == "__main__":
    main()
