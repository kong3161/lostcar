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
                         plate_number: str = "",
                         plate_prefix: str = "",
                         plate_province: str = "",
                         color: str = "",
                         reporter: str = ""):

    or_conditions = []

    if vehicle_type:
        or_conditions.append(f"vehicle_type.eq.{vehicle_type}")
    if brand:
        or_conditions.append(f"brand.ilike.*{brand}*")
    if model:
        or_conditions.append(f"model.ilike.*{model}*")
    if plate_number:
        or_conditions.append(f"plate_number.ilike.*{plate_number}*")
    if plate_prefix:
        or_conditions.append(f"plate_prefix.ilike.*{plate_prefix}*")
    if plate_province:
        or_conditions.append(f"plate_province.ilike.*{plate_province}*")
    if color:
        or_conditions.append(f"color.ilike.*{color}*")
    if reporter:
        or_conditions.append(f"reporter.ilike.*{reporter}*")

    or_query = ",".join(or_conditions)
    query = f"or=({or_query})" if or_query else ""
    url = f"{SUPABASE_URL}/rest/v1/reports?{query}&order=uploaded_at.desc"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        results = response.json() if response.status_code == 200 else []

    return templates.TemplateResponse("results.html", {
        "request": request,
        "results": results,
        "debug_url": url,
        "debug_status": response.status_code,
        "debug_raw": response.text
    })
