# pforge/agents/intent_router_agent.py
"""
This module contains the IntentRouterAgent. The IntentRouterAgent is
responsible for routing intents to the correct agent.
"""

from .base_agent import BaseAgent

class IntentRouterAgent(BaseAgent):
    """The IntentRouterAgent."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self):
        """Runs the agent."""
        pass
