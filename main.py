
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import httpx
from datetime import datetime
from urllib.parse import urlencode
from math import ceil

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

@app.get("/results", response_class=HTMLResponse)
async def show_results(
    request: Request,
    page: int = 1,
    vehicle_type: str = "",
    brand: str = "",
    model: str = "",
    date_lost: str = "",
    reporter: str = "",
    color: str = "",
    plate_number: str = "",
    engine_number: str = "",
    chassis_number: str = ""
):
    limit = 5
    offset = (page - 1) * limit

    filter_parts = []
    if vehicle_type:
        filter_parts.append(f"vehicle_type=eq.{vehicle_type}")
    if brand:
        filter_parts.append(f"brand=ilike.*{brand}*")
    if model:
        filter_parts.append(f"model=ilike.*{model}*")
    if date_lost:
        filter_parts.append(f"date_lost=eq.{date_lost}")
    if reporter:
        filter_parts.append(f"reporter=ilike.*{reporter}*")
    if color:
        filter_parts.append(f"color=ilike.*{color}*")
    if plate_number:
        filter_parts.append(f"plate_number=ilike.*{plate_number}*")
    if engine_number:
        filter_parts.append(f"engine_number=ilike.*{engine_number}*")
    if chassis_number:
        filter_parts.append(f"chassis_number=ilike.*{chassis_number}*")

    filter_query = "&".join(filter_parts)
    base_url = f"{SUPABASE_URL}/rest/v1/reports"
    url = f"{base_url}?{filter_query}&order=uploaded_at.desc&limit={limit}&offset={offset}" if filter_query else f"{base_url}?order=uploaded_at.desc&limit={limit}&offset={offset}"
    count_url = f"{base_url}?select=id&{filter_query}" if filter_query else f"{base_url}?select=id"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        count_response = await client.get(count_url, headers={**headers, "Prefer": "count=exact"})

    items = response.json() if response.status_code == 200 else []
    total = len(count_response.json()) if count_response.status_code == 200 else 0
    total_pages = ceil(total / limit) if total > 0 else 1

    return templates.TemplateResponse("results.html", {
        "request": request,
        "items": items,
        "debug_url": url,
        "debug_status": response.status_code,
        "debug_raw": response.text,
        "page": page,
        "total_pages": total_pages
    })
