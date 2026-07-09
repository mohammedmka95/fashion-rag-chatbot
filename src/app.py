"""
app.py
------
Terminal entry point for the Fashion Forward Hub chatbot.

Run with:
    python app.py

Type your messages at the "You:" prompt. Type "exit" (or "quit") at any
time to end the conversation.

Environment variables:
    GROQ_API_KEY        Required. Your Groq API key (https://console.groq.com/keys)
    WEAVIATE_ENABLED    Optional. Set to "false" to skip connecting to Weaviate
                         and run in FAQ-only mode. Defaults to "true".
"""

from dotenv import load_dotenv
import os
import sys

from chatbot.chatbot import FashionChatBot

load_dotenv()


def connect_to_weaviate():
    """
    Try to connect to a locally running Weaviate instance (used for product
    search). Returns None if Weaviate is unavailable or disabled, so the
    chatbot can still run in FAQ-only mode instead of crashing.
    """

    try:
        import weaviate

        client = weaviate.connect_to_local()
        print(f"Connected to Weaviate (client library version {weaviate.__version__}).\n")
        return client
    except Exception as e:
        print(
            "[warning] Could not connect to Weaviate — product search will be "
            f"unavailable, but FAQ questions will still work. Details: {e}\n"
        )
        return None


def main():
    # Fail fast with a clear message if the API key is missing.
    if not os.environ.get("GROQ_API_KEY"):
        print(
            "Error: GROQ_API_KEY environment variable is not set.\n"
            "Get a free key at https://console.groq.com/keys and set it with:\n"
            "  export GROQ_API_KEY='your_key_here'"
        )
        sys.exit(1)

    weaviate_client = connect_to_weaviate()

    try:
        bot = FashionChatBot(weaviate_client=weaviate_client)
    except Exception as e:
        print(f"Failed to start the chatbot: {e}")
        sys.exit(1)

    print(bot.initial_message["content"])
    print("(Type 'exit' to end the conversation.)\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit"):
                print("Goodbye!")
                break

            try:
                reply = bot.chat(user_input)
            except Exception as e:
                # Basic error handling: keep the conversation alive even if
                # a single turn fails (e.g. network hiccup, API error).
                reply = f"Sorry, something went wrong while processing that: {e}"

            print(f"Assistant: {reply}\n")
    finally:
        if weaviate_client is not None:
            weaviate_client.close()


if __name__ == "__main__":
    main()
