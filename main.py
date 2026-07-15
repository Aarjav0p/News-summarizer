import asyncio
import json
from openai import OpenAI
from dotenv import load_dotenv
import os

from web import get_world_news

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# Define the tool schema for chat.completions
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_world_news",
            "description": (
                "Fetches the latest global headlines from major news outlets "
                "(BBC, CNBC, NYT, Al Jazeera) simultaneously. "
                "Use this when the user asks about current events, world news, "
                "or what's happening in the world."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    }
]

# Map tool names to their callable functions
available_tools = {
    "get_world_news": lambda **kwargs: asyncio.run(get_world_news()),
}

messages = []


def main():
    while True:
        user_input = input("You: ")

        if user_input.lower().strip() in ["quit", "exit", "q"]:
            print("Assistant: Goodbye!")
            break

        messages.append({
            "role": "user",
            "content": user_input,
        })

        # --- Orchestration Loop ---
        # Keep calling the model until it gives a final text response
        # (i.e., no more tool calls).
        while True:
            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=messages,
                tool_choice="auto",
                tools=tools,
            )

            response_message = response.choices[0].message

            if not response_message.tool_calls:
                # No tool calls — model produced a final text answer
                break

            # Append the assistant's message (contains the tool_calls)
            messages.append(response_message)

            # Process each tool call
            for tool_call in response_message.tool_calls:
                print(f"  [Calling tool: {tool_call.function.name}...]")

                fn = available_tools.get(tool_call.function.name)
                if fn:
                    args = json.loads(tool_call.function.arguments)
                    result = fn(**args)
                else:
                    result = f"Error: Unknown tool '{tool_call.function.name}'"

                # Append the tool result back into the conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": result,
                })
            # Loop back to let the model read the tool output and respond

        # We exited the loop — the model gave a final text answer
        assistant_message = response_message.content
        messages.append({"role": "assistant", "content": assistant_message})
        print(f"Assistant: {assistant_message}")


if __name__ == "__main__":
    main()
