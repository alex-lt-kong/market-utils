"""FastAPI router for the Averaging Calculator: one page + a calc API."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from . import calc

SLUG = "averaging-calc"
_HERE = Path(__file__).resolve().parent

router = APIRouter()
templates = Jinja2Templates(directory=str(_HERE / "templates"))


@router.get("/", include_in_schema=False)
def page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "calculator.html", {})


@router.get("/api/calc")
def api_calc(qty: float, avg_cost: float, mkt_px: float, target_pct: float):
    try:
        return calc.plan(qty, avg_cost, mkt_px, target_pct)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
