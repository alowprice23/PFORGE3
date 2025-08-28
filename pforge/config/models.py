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
    def load(cls, config_dir: Path | str = "pforge/config") -> "Config":
        config_dir = Path(config_dir)

        with open(config_dir / "settings.yaml", "r") as f:
            settings_data = yaml.safe_load(f)

        with open(config_dir / "llm_providers.yaml", "r") as f:
            llm_providers_data = yaml.safe_load(f)

        with open(config_dir / "agents.yaml", "r") as f:
            agents_data = yaml.safe_load(f)

        with open(config_dir / "quotas.yaml", "r") as f:
            quotas_data = yaml.safe_load(f)

        return cls(
            settings=settings_data,
            llm_providers=llm_providers_data,
            agents=agents_data,
            quotas=quotas_data,
        )
