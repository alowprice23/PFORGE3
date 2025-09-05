# pforge/agents/intent_router_agent.py
"""
This module contains the IntentRouterAgent. The IntentRouterAgent is
responsible for routing intents to the correct agent.
"""
import os
import asyncio
from pforge.llm_clients.claude_client import ClaudeClient
from pforge.orchestrator.signals import Message
from .base_agent import BaseAgent
import json

class IntentRouterAgent(BaseAgent):
    """The IntentRouterAgent."""
    name: str = "intent_router"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.claude_client = None

    async def on_startup(self):
        """Initializes the Claude client."""
        self.logger.info("IntentRouterAgent starting up...")
        api_key = os.getenv("ANTHROPIC_API_KEY")

        self.logger.info("Loading agent skills...")
        from pforge.cli import agent_skills as skills
        self.available_skills = {
            "run_tests": skills.run_tests,
            "list_files": skills.list_files,
            "read_file": skills.read_file,
            "apply_patch": skills.apply_patch,
        }
        self.logger.info("Skills loaded.")

        self.logger.info("Initializing Claude client...")
        self.claude_client = ClaudeClient(api_key=api_key)
        self.logger.info("Claude client initialized.")

        self.logger.info("Subscribing to chat_input topic...")
        self.bus.subscribe(self.name, "chat_input")
        self.logger.info("Subscribed to chat_input topic.")
        self.logger.info("IntentRouterAgent startup complete.")


    async def on_tick(self):
        """Checks for incoming chat messages and routes them."""
        if not self.claude_client:
            return

        while True:
            message = await self.bus.get(self.name, timeout=0.1)
            if not message:
                break
            self.logger.info(f"Processing message: {message.payload}")
            user_prompt = message.payload.get("prompt")
            if not user_prompt:
                continue

            # This is a simplified version of the chat loop from pforge/cli/chat.py
            try:
                system_prompt = self.config.prompts['intent_router']['system']
                user_prompt_template = self.config.prompts['intent_router']['user']

                tool_names = ", ".join(self.available_skills.keys())
                formatted_user_prompt = user_prompt_template.format(tools=tool_names, user_prompt=user_prompt)

                response = await self.claude_client.chat(
                    [{"role": "user", "content": formatted_user_prompt}],
                    system=system_prompt,
                    max_tokens=10
                )

                tool_name = response.strip()
                if tool_name in self.available_skills:
                    self.logger.info(f"Routing to tool: {tool_name}")
                    # For now, we'll assume no input is needed for the skills
                    await self.publish(
                        tool_name,
                        Message(type="execute_skill", payload={"input": {}})
                    )
                else:
                    await self.publish(
                        "chat_output",
                        Message(type="chat_response", payload={"response": f"I'm sorry, I don't know how to do that. I can {tool_names}."})
                    )
            except Exception as e:
                self.logger.error(f"Error routing intent: {e}")
                await self.publish(
                    "chat_output",
                    Message(type="chat_response", payload={"response": f"An error occurred: {e}"})
                )
