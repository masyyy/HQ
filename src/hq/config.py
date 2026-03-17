from pathlib import Path
import json

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import tomli_w

HQ_DIR = Path.home() / ".hq"
CONFIG_PATH = HQ_DIR / "config.toml"

DEFAULT_STAGES: dict[str, list[str]] = {
    "crm": ["lead", "contacted", "qualified", "proposal", "negotiating", "closed_won", "closed_lost"],
    "board": ["backlog", "todo", "in_progress", "review", "done"],
}


def _ensure_dir() -> None:
    HQ_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return tomllib.loads(CONFIG_PATH.read_text())


def save_config(config: dict) -> None:
    _ensure_dir()
    CONFIG_PATH.write_bytes(tomli_w.dumps(config).encode())


def get_stages(module: str) -> list[str]:
    config = load_config()
    stages = config.get("stages", {}).get(module)
    if stages:
        return stages
    return DEFAULT_STAGES[module]


def validate_stage(module: str, stage: str) -> bool:
    return stage in get_stages(module)
