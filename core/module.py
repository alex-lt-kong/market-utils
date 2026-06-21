"""The interface every plugin under modules/ exposes as a `MODULE` constant.

The host (core/main.py) discovers these, mounts each router at /<slug>, mounts
its static dir, and enters its `lifespan` for the life of the app. Everything
else — data, schedulers, templates — stays private to the module.
"""

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import APIRouter


@dataclass(frozen=True)
class Module:
    slug: str                 # URL segment, e.g. "pe-monitor"
    name: str                 # display name, e.g. "P/E Monitor"
    description: str          # one-line landing-card text
    router: APIRouter         # included at prefix=/<slug>, tags=[name]
    order: int = 100          # lower sorts earlier on the landing page
    icon: Optional[str] = None
    static_dir: Optional[str] = None   # abs path mounted at /<slug>/static
    static_name: Optional[str] = None  # url_for name (match the template)
    # Zero-arg callable returning a context manager that owns the module's
    # resources (scheduler, db). Entered on startup, exited on shutdown.
    lifespan: Optional[Callable[[], AbstractContextManager]] = None
