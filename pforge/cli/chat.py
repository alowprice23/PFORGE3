from __future__ import annotations

import asyncio
import os
import threading
from rich.console import Console
from rich.text import Text

from pforge.config import Config
from pforge.project import Project
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.orchestrator.signals import Message
from pforge.agents.intent_router_agent import IntentRouterAgent
from . import agent_skills as skills

console = Console()

def start_chat_repl():
    """
    Starts the interactive Read-Eval-Print Loop (REPL) for chatting with pForge.
    """
    console.print(Text("Welcome to the pForge Interactive Chat.", style="bold green"))
    console.print("Type your requests or questions below. Type 'exit' or 'quit' to end.")

    # Basic setup for running agents standalone
    try:
        config = Config.load()
    except FileNotFoundError:
        # If the config file is not found, create a default one for the chat to work
        config = Config(
            llm=LLMConfig(model="gpt-4-turbo"),
            doctor=DoctorConfig(retry_limit=3),
            specifications=SpecificationsConfig(raw_config={}),
            recovery=RecoveryConfig(enabled=False, checks=[])
        )
    project = Project(".")
    bus = InMemoryBus()

    # Instantiate and run agents in the background
    intent_router = IntentRouterAgent(bus=bus, config=config, project=project)

    # For now, we'll create a simple skill dispatcher agent
    async def skill_dispatcher():
        bus.subscribe("dispatcher", "run_tests")
        bus.subscribe("dispatcher", "list_files")
        bus.subscribe("dispatcher", "read_file")
        bus.subscribe("dispatcher", "apply_patch")

        while True:
            for topic in ["run_tests", "list_files", "read_file", "apply_patch"]:
                while True:
                    msg = await bus.get("dispatcher", timeout=0.1)
                    if not msg:
                        break
                    skill_name = topic
                    skill_input = msg.payload.get("input", {})
                    console.print(Text(f"Executing skill: {skill_name} with input: {skill_input}", style="yellow"))

                    skill_function = getattr(skills, skill_name, None)
                    if skill_function:
                        try:
                            result = skill_function(**skill_input)
                            await bus.publish("chat_output", Message(type="chat_response", payload={"response": result}))
                        except Exception as e:
                            await bus.publish("chat_output", Message(type="chat_response", payload={"response": f"Error: {e}"}))
                    else:
                        await bus.publish("chat_output", Message(type="chat_response", payload={"response": f"Error: Skill '{skill_name}' not found."}))
            await asyncio.sleep(0.1)


    def run_agents():
        print("Starting agent thread...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        print("Event loop created and set.")
        try:
            loop.run_until_complete(asyncio.gather(
                intent_router.run_loop(),
                skill_dispatcher()
            ))
        except Exception as e:
            print(f"Error in agent thread: {e}")
        print("Agent thread finished.")

    agent_thread = threading.Thread(target=run_agents, daemon=True)
    agent_thread.start()

    async def chat_loop():
        bus.subscribe("chat_cli", "chat_output")

        while True:
            prompt_text = await asyncio.to_thread(console.input, "You> ")
            if prompt_text.lower() in ["exit", "quit"]:
                break

            await bus.publish("chat_input", Message(type="chat_prompt", payload={"prompt": prompt_text}))

            # Wait for a response
            while True:
                msg = await bus.get("chat_cli", timeout=10)
                if msg:
                    console.print(Text(f"pForge: {msg.payload.get('response')}", style="bold blue"))
                    break
                else:
                    console.print(Text("pForge is thinking...", style="italic yellow"))

    asyncio.run(chat_loop())

    console.print(Text("\nExiting pForge chat. Goodbye!", style="bold green"))
