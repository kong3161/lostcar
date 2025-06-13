
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter
import os
import httpx

router = APIRouter()
templates = Jinja2Templates(directory="templates")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

@router.get("/search", response_class=HTMLResponse)
async def search_form(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

@router.get("/results", response_class=HTMLResponse)
async def search_results(request: Request,
                         vehicle_type: str = "",
                         brand: str = "",
                         model: str = "",
                         date_lost: str = "",
                         reporter: str = ""):

    # Build query string
    filters = []
    if vehicle_type:
        filters.append(f'vehicle_type=eq.{vehicle_type}')
    if brand:
        filters.append(f'brand=ilike.*{brand}*')
    if model:
        filters.append(f'model=ilike.*{model}*')
    if date_lost:
        filters.append(f'date_lost=eq.{date_lost}')
    if reporter:
        filters.append(f'reporter=ilike.*{reporter}*')

    query = "&".join(filters)
    url = f"{SUPABASE_URL}/rest/v1/reports?{query}&order=date_lost.desc"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        results = response.json() if response.status_code == 200 else []

    return templates.TemplateResponse("results.html", {
        "request": request,
        "results": results
    })
