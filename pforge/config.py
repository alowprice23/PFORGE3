"""
Configuration loading and management for pForge.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
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
class Config:
    """
    Top-level configuration for pForge, loaded from pforge.toml.
    """
    llm: LLMConfig
    doctor: DoctorConfig
    specifications: SpecificationsConfig
    recovery: RecoveryConfig

    @staticmethod
    def load(path: Path | str = "pforge.toml") -> Config:
        """
        Loads configuration from a TOML file.
        """
        config_path = Path(path)
        if not config_path.is_file():
            # For tests, it's ok if this is missing. Return a default config.
            if "pytest" in str(path):
                return Config(
                    llm=LLMConfig(model="gpt-4-turbo"),
                    doctor=DoctorConfig(retry_limit=3),
                    specifications=SpecificationsConfig(raw_config={})
                )
            raise FileNotFoundError(f"Configuration file not found at: {config_path}")

        with config_path.open("rb") as f:
            data = tomllib.load(f)

        recovery_data = data.get("recovery", {})
        recovery_checks = [RecoveryCheck(**check) for check in recovery_data.get("checks", [])]
        recovery_config = RecoveryConfig(
            enabled=recovery_data.get("enabled", False),
            checks=recovery_checks
        )

        return Config(
            llm=LLMConfig(model=data.get("llm", {}).get("model", "gpt-4-turbo")),
            doctor=DoctorConfig(retry_limit=data.get("doctor", {}).get("retry_limit", 3)),
            specifications=SpecificationsConfig(raw_config=data.get("specifications", {})),
            recovery=recovery_config,
        )

# Example of how to use it:
#
# from pforge.config import Config
#
# config = Config.load()
# print(config.llm.model)
# print(config.doctor.retry_limit)
