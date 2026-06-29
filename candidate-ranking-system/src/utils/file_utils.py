"""
File Utilities
Helpers for loading configuration, reading files, and managing paths.
"""

import yaml
from pathlib import Path
from typing import Any, Union
from src.utils.logger import get_logger

logger = get_logger("file_utils")

# Project root (candidate-ranking-system/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_yaml(filepath: Union[str, Path]) -> dict:
    """Load a YAML configuration file."""
    path = Path(filepath)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        logger.warning(f"Config file not found: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(name: str) -> dict:
    """Load a named configuration from configs/ directory."""
    return load_yaml(PROJECT_ROOT / "configs" / f"{name}.yaml")


def ensure_dir(path: Union[str, Path]) -> Path:
    """Ensure directory exists, creating if necessary."""
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def resolve_path(path: Union[str, Path]) -> Path:
    """Resolve a path relative to project root."""
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def get_data_path(filename: str) -> Path:
    """Get path to a file in data/raw/ directory."""
    # First check if it's in the project data/raw/ directory
    project_path = PROJECT_ROOT / "data" / "raw" / filename
    if project_path.exists():
        return project_path
    # Fall back to the parent Resume Ranker directory
    parent_path = PROJECT_ROOT.parent / filename
    if parent_path.exists():
        return parent_path
    logger.warning(f"Data file not found: {filename}")
    return project_path  # Return expected path even if not found


class Config:
    """Unified configuration manager."""

    _instance = None
    _config = {}  # type: dict

    @classmethod
    def load(cls) -> "Config":
        """Load all configuration files."""
        if cls._instance is None:
            cls._instance = cls()
            cls._config = {
                "runtime": load_config("runtime"),
                "models": load_config("models"),
                "pipeline": load_config("pipeline"),
            }
            logger.info("Configuration loaded successfully")
        return cls._instance

    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """Get a configuration value."""
        data = self._config.get(section, {})
        if key is None:
            return data
        # Support nested keys with dot notation
        keys = key.split(".")
        for k in keys:
            if isinstance(data, dict):
                data = data.get(k, default)
            else:
                return default
        return data if data is not None else default

    @property
    def runtime(self) -> dict:
        return self._config.get("runtime", {})

    @property
    def models(self) -> dict:
        return self._config.get("models", {})

    @property
    def pipeline(self) -> dict:
        return self._config.get("pipeline", {})
