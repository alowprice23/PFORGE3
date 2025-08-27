"""
Configuration loading and management for pForge.
"""
from __future__ import annotations

import os
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
class Config:
    """
    Top-level configuration for pForge, loaded from pforge.toml.
    """
    llm: LLMConfig
    doctor: DoctorConfig

    @staticmethod
    def load(path: Path | str = "pforge.toml") -> Config:
        """
        Loads configuration from a TOML file.
        """
        config_path = Path(path)
        if not config_path.is_file():
            raise FileNotFoundError(f"Configuration file not found at: {config_path}")

        with config_path.open("rb") as f:
            data = tomllib.load(f)

        return Config(
            llm=LLMConfig(model=data.get("llm", {}).get("model", "gpt-4-turbo")),
            doctor=DoctorConfig(retry_limit=data.get("doctor", {}).get("retry_limit", 3)),
        )

# Example of how to use it:
#
# from pforge.config import Config
#
# config = Config.load()
# print(config.llm.model)
# print(config.doctor.retry_limit)
