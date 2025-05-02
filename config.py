# config.py

import yaml
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ModelConfig:
    high: str
    low: str

@dataclass
class ProviderConfig:
    api_key_env: str
    endpoint_env: Optional[str] = None
    models: ModelConfig

class AppConfig:
    def __init__(self, path: str = "config.yaml"):
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        self.preferred_provider: str = data["preferred_provider"]
        self.providers: Dict[str, ProviderConfig] = {}

        for name, cfg in data.get("providers", {}).items():
            m = cfg.get("models", {})
            models = ModelConfig(high=m.get("high"), low=m.get("low"))
            api_key_env = cfg.get("api_key_env")
            endpoint_env = cfg.get("api_endpoint_env")  # only used by Azure

            self.providers[name] = ProviderConfig(
                api_key_env=api_key_env,
                endpoint_env=endpoint_env,
                models=models
            )

# Global singleton
CONFIG = AppConfig()
