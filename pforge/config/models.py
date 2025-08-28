from __future__ import annotations
from pydantic import BaseModel
import yaml
from pathlib import Path

class Config(BaseModel):
    settings: dict
    llm_providers: dict
    agents: dict
    quotas: dict

    @classmethod
    def from_yaml(cls, path: Path) -> "Config":
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)

def load_config() -> Config:
    config_path = Path(__file__).parent / "settings.yaml"
    # This is a simplified loader. A real implementation would merge multiple files.
    with open(config_path, "r") as f:
        settings_data = yaml.safe_load(f)

    # In a real app, you would load all the other yaml files here too.
    # For now, we'll just use the settings data for all fields.
    return Config(
        settings=settings_data,
        llm_providers={},
        agents={},
        quotas={},
    )
