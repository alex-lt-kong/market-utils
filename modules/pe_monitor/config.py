"""Load and resolve module config. Shared between the app and backfill/ tools."""

import tomllib
from pathlib import Path


def load_config(path: str = "config.toml") -> dict:
    base = Path(__file__).parent
    fp = base / path
    if not fp.exists():
        raise FileNotFoundError(
            f"{fp} not found — copy the sample: "
            f"cp {base / 'config.sample.toml'} {fp}"
        )
    with open(fp, "rb") as f:
        cfg = tomllib.load(f)
    cfg["database_path"] = str(base / cfg["database_path"])
    return cfg
