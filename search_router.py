from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter
import os
import httpx
from math import ceil

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
                         reporter: str = "",
                         page: int = 1):

    filter_conditions = []

    if vehicle_type:
        filter_conditions.append(f"vehicle_type=eq.{vehicle_type}")
    if brand:
        filter_conditions.append(f"brand=ilike.*{brand}*")
    if model:
        filter_conditions.append(f"model=ilike.*{model}*")
    if plate_number:
        filter_conditions.append(f"plate_number=ilike.*{plate_number}*")
    if plate_prefix:
        filter_conditions.append(f"plate_prefix=ilike.*{plate_prefix}*")
    if plate_province:
        filter_conditions.append(f"plate_province=ilike.*{plate_province}*")
    if color:
        filter_conditions.append(f"color=ilike.*{color}*")
    if reporter:
        filter_conditions.append(f"reporter=ilike.*{reporter}*")

    query = "&".join(filter_conditions)

    page_size = 5
    offset = (page - 1) * page_size

    if query:
        paginated_query = f"{query}&order=uploaded_at.desc&limit={page_size}&offset={offset}"
        count_query = f"{query}&select=id&count=exact"
    else:
        paginated_query = f"order=uploaded_at.desc&limit={page_size}&offset={offset}"
        count_query = "select=id&count=exact"

    url = f"{SUPABASE_URL}/rest/v1/reports?{paginated_query}"
    count_url = f"{SUPABASE_URL}/rest/v1/reports?{count_query}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        count_response = await client.get(count_url, headers=headers)

        results = response.json() if response.status_code == 200 else []

        total_count = 0
        if count_response.status_code == 200:
            content_range = count_response.headers.get("content-range", "")
            if "/" in content_range:
                total_count = int(content_range.split("/")[-1])
        total_pages = ceil(total_count / page_size)

    return templates.TemplateResponse("results.html", {
        "request": request,
        "results": results,
        "debug_url": url,
        "debug_status": response.status_code,
        "debug_raw": response.text,
        "page": page,
        "total_pages": total_pages
    })