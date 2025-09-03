from __future__ import annotations

import asyncio
import json
import os

from rich.console import Console
from rich.text import Text

from pforge.llm_clients.claude_client import ClaudeClient
from . import agent_skills as skills

console = Console()

# Create a mapping from skill names to the actual functions
AVAILABLE_SKILLS = {
    "run_tests": skills.run_tests,
    "list_files": skills.list_files,
    "read_file": skills.read_file,
    "apply_patch": skills.apply_patch,
}

def start_chat_repl():
    """
    Starts the interactive Read-Eval-Print Loop (REPL) for chatting with pForge.
    """
    console.print(Text("Welcome to the pForge Interactive Chat.", style="bold green"))
    console.print("Type your requests or questions below. Type 'exit' or 'quit' to end.")

    # Load the API key from an environment variable
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print(Text("Error: ANTHROPIC_API_KEY environment variable not set.", style="bold red"))
        return

    # Pass the list of skill functions to the client
    claude_client = ClaudeClient(api_key=api_key, tools=list(AVAILABLE_SKILLS.values()))

    async def chat_loop():
        # Hardcode the prompt for testing
        try:
            with open("pforge/cli/patch.txt", "r") as f:
                patch_content = f.read()
            prompt_text = f"Excellent. Here is the patch you generated. Please apply it to the codebase.\n\n{patch_content}"
        except FileNotFoundError:
            prompt_text = "Hello! What can I help you with today?"

        console.print(f"You> {prompt_text}")

        messages = [{"role": "user", "content": prompt_text}]

        try:
            while True:
                response = await claude_client.chat(messages, max_tokens=4096)

                # Append the assistant's response to the message history
                # The response from the API is not a dict, so we need to convert it.
                # The content can be a list of blocks (text, tool_use).
                response_content = []
                for block in response.content:
                    if block.type == "text":
                        response_content.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        response_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })

                messages.append({"role": response.role, "content": response_content})

                if response.stop_reason != "tool_use":
                    # If the model is done, break the loop and print the final text
                    break

                console.print(Text("pForge wants to use a tool...", style="italic yellow"))

                tool_results_content = []
                for tool_call in response.content:
                    if tool_call.type == "tool_use":
                        tool_name = tool_call.name
                        tool_input = tool_call.input
                        tool_id = tool_call.id

                        console.print(Text(f"  Tool: {tool_name}, Input: {tool_input}", style="yellow"))

                        if tool_name in AVAILABLE_SKILLS:
                            skill_function = AVAILABLE_SKILLS[tool_name]
                            try:
                                result = skill_function(**tool_input)
                                if isinstance(result, dict):
                                    result = json.dumps(result, indent=2)
                            except Exception as e:
                                result = f"Error executing tool {tool_name}: {e}"

                            tool_results_content.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": str(result),
                            })
                        else:
                            tool_results_content.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": f"Error: Tool '{tool_name}' not found.",
                                "is_error": True,
                            })

                # Add the tool results to the message history to continue the conversation
                messages.append({"role": "user", "content": tool_results_content})
                console.print(Text("Sending tool results back to pForge...", style="italic yellow"))

            # After the loop, the last response should be a text response
            final_text = ""
            for block in response.content:
                if block.type == "text":
                    final_text += block.text + "\n"

            console.print(Text("pForge:", style="bold blue"), final_text)

        except Exception as e:
            console.print(Text(f"Error during API call: {e}", style="bold red"))


    asyncio.run(chat_loop())

    console.print(Text("\nExiting pForge chat. Goodbye!", style="bold green"))
