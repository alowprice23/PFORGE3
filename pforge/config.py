"""
Configuration loading and management for pForge.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import toml
import yaml
from typing import Any, Dict

@dataclass
class LLMConfig:
    """LLM-related configuration."""
    model: str

@dataclass
class DoctorConfig:
    """Configuration for the 'doctor' command."""
    retry_limit: int

@dataclass
class SpecificationsConfig:
    """Represents the 'specifications' block in the config."""
    raw_config: Dict[str, Any]

@dataclass
class RecoveryCheck:
    """Represents a single check in the recovery config."""
    detector: str
    action: str

@dataclass
class RecoveryConfig:
    """Represents the 'recovery' block in the config."""
    enabled: bool
    checks: list[RecoveryCheck]

@dataclass
class BudgetConfig:
    """Represents the 'budget' block in the config."""
    tenant: str
    daily_quota_tokens: int

@dataclass
class PlannerConfig:
    """Represents the 'planner' block in the config."""
    effort_budget_per_tick: float

@dataclass
class Config:
    """
    Top-level configuration for pForge, loaded from pforge.toml.
    """
    llm: LLMConfig
    doctor: DoctorConfig
    specifications: SpecificationsConfig
    recovery: RecoveryConfig
    budget: BudgetConfig
    planner: PlannerConfig
    prompts: Dict[str, Any]

    @staticmethod
    def load(path: Path | str = "pforge.yaml") -> Config:
        """
        Loads configuration from a YAML file.
        """
        config_path = Path(path)
        if not config_path.is_file():
            return Config(
                llm=LLMConfig(model="gpt-4-turbo"),
                doctor=DoctorConfig(retry_limit=3),
                specifications=SpecificationsConfig(raw_config={}),
                recovery=RecoveryConfig(enabled=False, checks=[]),
                budget=BudgetConfig(tenant="pforge-dev", daily_quota_tokens=1_000_000),
                planner=PlannerConfig(effort_budget_per_tick=30.0),
                prompts={},
            )

        with config_path.open("r") as f:
            if config_path.suffix == ".toml":
                data = toml.load(f)
            else:
                data = yaml.safe_load(f)

        recovery_data = data.get("recovery", {})
        recovery_checks = [RecoveryCheck(**check) for check in recovery_data.get("checks", [])]
        recovery_config = RecoveryConfig(
            enabled=recovery_data.get("enabled", False),
            checks=recovery_checks
        )

        return Config(
            llm=LLMConfig(**data.get("llm", {"model": "gpt-4-turbo"})),
            doctor=DoctorConfig(**data.get("doctor", {"retry_limit": 3})),
            specifications=SpecificationsConfig(raw_config=data.get("specifications", {})),
            recovery=recovery_config,
            budget=BudgetConfig(**data.get("budget", {"tenant": "pforge-dev", "daily_quota_tokens": 1_000_000})),
            planner=PlannerConfig(**data.get("planner", {"effort_budget_per_tick": 30.0})),
            prompts=data.get("prompts", {}),
        )

# Example of how to use it:
#
# from pforge.config import Config
#
# config = Config.load()
# print(config.llm.model)
# print(config.doctor.retry_limit)
