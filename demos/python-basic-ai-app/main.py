from openai import OpenAI
import argparse
import os
import sys


DEFAULT_MODEL="docker.io/ai/gemma4:E4B"
DEFAULT_BASE_URL="http://localhost:12434/v1"

SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer directly and concisely, and provide code examples when relevant. "
    "Do not add any formatting like markdown or code blocks. "
    "Ask a follow-up question if the user query is ambiguous or incomplete. "
)


def main():
    

    parser = argparse.ArgumentParser(description="Run a basic AI app.")
    parser.add_argument("--model", type=str, default=os.environ.get("MODEL", DEFAULT_MODEL), help="Model to use")
    parser.add_argument("--base-url", type=str, default=os.environ.get("BASE_URL", DEFAULT_BASE_URL), help="Base URL for the API")
    args = parser.parse_args()

    print(f"Using model: {args.model}")
    print(f"Using base URL: {args.base_url}")

    # Here you would add the logic to interact with the AI model using the specified base URL and model.
    client = OpenAI(base_url=args.base_url, api_key="YOUR_API_KEY_HERE")
    messages:list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT}
        ]
    print(f"Chatting with model {args.model} at {args.base_url}... type 'exit' to quit.")

    reply_chunks:list[str] = []
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break

        messages.append({"role": "user", "content": user_input})
        print("Waiting for response...")
        stream = client.chat.completions.create(
            model=args.model,
            messages=messages,
            stream=True
        )
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                print(token, end="", flush=True)
                reply_chunks.append(token)
        print()  # Print a newline after the response
        messages.append({"role": "assistant", "content": "".join(reply_chunks)})


if __name__ == "__main__":
    main()