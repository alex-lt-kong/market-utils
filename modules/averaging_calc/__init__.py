"""Averaging Calculator module: exposes MODULE for the host to discover."""

from core.module import Module

from . import views

MODULE = Module(
    slug=views.SLUG,
    name="Pyramiding Calculator",
    description="Shares to add at market to move a position's P/L% from its current level to a target.",
    router=views.router,
    order=20,
    icon="🗻",
)
