"""Host config: bind address, cookie secret, and shared auth tokens.

The config file is mandatory and chosen explicitly via `python -m core --config
<path>` (which sets MARKET_UTILS_CONFIG). Defaults only fill in keys the file
omits. When auth is enabled the secret_key must be strong, otherwise the signed
session cookie is forgeable. Module-specific config stays inside each module.
"""

import os
import tomllib
from pathlib import Path

_ENV_VAR = "MARKET_UTILS_CONFIG"
_DEFAULT_SECRET = "dev-insecure-change-me"
_MIN_SECRET_LEN = 16

_DEFAULTS = {
    "host": "127.0.0.1",
    "port": 9090,
    "secret_key": _DEFAULT_SECRET,
    "auth_tokens": [],
}


def config_source(path: str | None = None) -> str:
    chosen = path or os.environ.get(_ENV_VAR)
    if not chosen:
        raise RuntimeError(
            f"No host config specified. Run `python -m core --config <path>` "
            f"or set {_ENV_VAR}."
        )
    return chosen


def _validate(cfg: dict) -> None:
    if cfg["auth_tokens"]:
        sk = cfg["secret_key"]
        if not sk or sk == _DEFAULT_SECRET or len(sk) < _MIN_SECRET_LEN:
            raise RuntimeError(
                "auth_tokens are set but secret_key is missing, default, or too "
                "short — the session cookie would be forgeable. Set a strong "
                "secret_key (>= 16 chars), e.g.\n"
                '  python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )


def load_config(path: str | None = None) -> dict:
    fp = Path(config_source(path))
    if not fp.exists():
        raise FileNotFoundError(f"Host config not found: {fp}")
    cfg = dict(_DEFAULTS)
    with open(fp, "rb") as f:
        cfg.update(tomllib.load(f))
    _validate(cfg)
    return cfg
