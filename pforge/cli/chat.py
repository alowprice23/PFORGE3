from __future__ import annotations
import os
import asyncio
import typer
from rich.console import Console
from rich.text import Text
from pforge.llm_clients.claude_client import ClaudeClient

console = Console()

def start_chat_repl():
    """
    Starts the interactive Read-Eval-Print Loop (REPL) for chatting with pForge.
    """
    console.print(Text("Welcome to the pForge Interactive Chat.", style="bold green"))
    console.print("Type your requests or questions below. Type 'exit' or 'quit' to end.")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print(Text("Error: ANTHROPIC_API_KEY environment variable not set.", style="bold red"))
        raise typer.Exit(code=1)

    claude_client = ClaudeClient(api_key=api_key)

    async def chat_loop():
        import re
        from pathlib import Path
        import subprocess

        fix_pattern = re.compile(r"fix file '(.+?)' with error '(.+?)'")

        while True:
            try:
                prompt_text = await asyncio.to_thread(typer.prompt, "You", prompt_suffix="> ")

                if prompt_text.lower() in ["exit", "quit"]:
                    break

                match = fix_pattern.match(prompt_text)
                if match:
                    file_path_str, error_message = match.groups()
                    file_path = Path(file_path_str)

                    if not file_path.exists():
                        console.print(Text(f"Error: File not found at {file_path_str}", style="bold red"))
                        continue

                    file_content = file_path.read_text()

                    fix_prompt = (
                        f"The following file has a bug:\n\n"
                        f"File: {file_path_str}\n"
                        f"Content:\n```\n{file_content}\n```\n\n"
                        f"The error message is:\n```\n{error_message}\n```\n\n"
                        f"Please provide the corrected code for the entire file. Do not add any extra explanations, just the code."
                    )

                    messages = [{"role": "user", "content": fix_prompt}]

                    try:
                        console.print(Text("pForge: Thinking...", style="bold yellow"))
                        suggested_fix = await claude_client.chat(messages, max_tokens=4096)

                        console.print(Text("pForge: I have a suggested fix:", style="bold blue"))
                        console.print(suggested_fix)

                        if typer.confirm("Apply this fix?"):
                            subprocess.run(
                                ["python", "-m", "pforge.cli.main", "fix", "apply", file_path_str, suggested_fix],
                                check=True
                            )
                        else:
                            console.print(Text("Fix not applied.", style="yellow"))

                    except Exception as e:
                        console.print(Text(f"Error during API call: {e}", style="bold red"))
                else:
                    messages = [{"role": "user", "content": prompt_text}]
                    try:
                        response_text = await claude_client.chat(messages, max_tokens=2048)
                        console.print(Text("pForge:", style="bold blue"), response_text)
                    except Exception as e:
                        console.print(Text(f"Error during API call: {e}", style="bold red"))

            except (KeyboardInterrupt, EOFError):
                break

    asyncio.run(chat_loop())

    console.print(Text("\nExiting pForge chat. Goodbye!", style="bold green"))
