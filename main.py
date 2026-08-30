"""
main.py
-------
Phase 1 entry point: a text chat loop with your personal AI.

Run it with:  python main.py
"""

from ai_brain import config, memory, commands, ai_client, auth


def main():
    if not auth.prompt_and_verify():
        print("Too many failed attempts. Exiting.")
        return

    print(f"=== {config.ASSISTANT_NAME} (Phase 1: Brain) ===")
    print("Type /help for commands, /quit to exit.\n")

    history = memory.load_history()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if commands.is_command(user_input):
            try:
                result = commands.run_command(user_input)
                print(f"{config.ASSISTANT_NAME}: {result}\n")
            except SystemExit:
                print("Goodbye!")
                break
            continue

        history = memory.append_message(history, "user", user_input)
        reply = ai_client.get_ai_reply(history)
        history = memory.append_message(history, "assistant", reply)

        print(f"{config.ASSISTANT_NAME}: {reply}\n")


if __name__ == "__main__":
    main()
