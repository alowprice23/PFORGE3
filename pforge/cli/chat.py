from __future__ import annotations
import httpx
import typer
from rich.console import Console
from rich.text import Text

console = Console()

# The base URL for the pForge API server.
# This would be configurable in a real application.
API_BASE_URL = "http://localhost:8000"

def start_chat_repl():
    """
    Starts the interactive Read-Eval-Print Loop (REPL) for chatting with pForge.
    """
    console.print(Text("Welcome to the pForge Interactive Chat.", style="bold green"))
    console.print("Type your requests or questions below. Type 'exit' or 'quit' to end.")

    # Create a persistent httpx client for the session
    with httpx.Client(base_url=API_BASE_URL, timeout=30.0) as client:
        while True:
            try:
                # Use Typer's prompt for a nice input experience
                prompt_text = typer.prompt("You", prompt_suffix="> ")

                if prompt_text.lower() in ["exit", "quit"]:
                    break

                # Send the user's message to the backend
                try:
                    response = client.post(
                        "/api/chat/nl", # Matches the route in server/routes/chat.py
                        json={"msg": prompt_text}
                    )
                    response.raise_for_status()

                    # For now, we'll just print the raw response.
                    # A more advanced client would listen on the SSE or WebSocket
                    # stream for a more detailed, asynchronous reply.
                    console.print(Text("pForge:", style="bold blue"), response.json())

                except httpx.RequestError as e:
                    console.print(Text(f"Error: Could not connect to the pForge server at {API_BASE_URL}.", style="bold red"))
                    console.print(Text(f"Details: {e}", style="red"))
                    console.print("Please ensure the server is running with 'uvicorn pforge.server.app:app'.")
                except httpx.HTTPStatusError as e:
                    console.print(Text(f"Error: Received an error response from the server (Status {e.response.status_code}).", style="bold red"))
                    console.print(f"Response: {e.response.text}")

            except (KeyboardInterrupt, EOFError):
                break

    console.print(Text("\nExiting pForge chat. Goodbye!", style="bold green"))
