from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
import httpx
from datetime import datetime
from urllib.parse import urlencode
from math import ceil
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/submit")
async def submit(
    request: Request,
    vehicle_type: str = Form(...),
    brand: str = Form(...),
    model: str = Form(...),
    color: str = Form(""),
    plate_prefix: str = Form(""),
    plate_number: str = Form(""),
    plate_province: str = Form(""),
    engine_number: str = Form(""),
    chassis_number: str = Form(""),
    date_lost: str = Form(""),
    time_event: str = Form(""),
    time_reported: str = Form(""),
    location: str = Form(""),
    lat: str = Form(""),
    lng: str = Form(""),
    reporter: str = Form(""),
    details: str = Form(""),
    files: list[UploadFile] = File(None)
):
    from supabase import create_client
    from uuid import uuid4
    from fastapi.responses import RedirectResponse

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    supabase = create_client(url, key)

    try:
        uploaded_urls = []
        # อัปโหลดไฟล์
        if files:
            cloudinary.config(
                cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
                api_key=os.getenv("CLOUDINARY_API_KEY"),
                api_secret=os.getenv("CLOUDINARY_API_SECRET")
            )
            for file in files:
                contents = await file.read()
                result = cloudinary.uploader.upload(contents, resource_type="image")
                public_url = result["secure_url"]
                uploaded_urls.append(public_url)

        data = {
            "vehicle_type": vehicle_type,
            "brand": brand,
            "model": model,
            "color": color,
            "plate_prefix": plate_prefix,
            "plate_number": plate_number,
            "plate_province": plate_province,
            "engine_number": engine_number,
            "chassis_number": chassis_number,
            "date_lost": date_lost or None,
            "time_event": time_event,
            "time_reported": time_reported,
            "location": location,
            "lat": lat,
            "lng": lng,
            "reporter": reporter,
            "details": details,
            "uploaded_at": datetime.utcnow().isoformat(),
            "image_urls": uploaded_urls
        }

        result = supabase.table("reports").insert(data).execute()
        if not result.data or not isinstance(result.data, list):
            return JSONResponse(status_code=500, content={"error": "❌ Insert failed", "details": result.__dict__})

        report_id = result.data[0]["id"]

        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/?success=true", status_code=303)

    except Exception as e:
        return RedirectResponse(url="/?success=false", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})
@app.get("/dashboard-data")
async def dashboard_data():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SUPABASE_URL}/rest/v1/reports?select=vehicle_type,model,time_reported", headers=headers)

    data = response.json()

    # แยกข้อมูลรุ่นตามประเภทรถ
    models_by_type = {}
    time_ranges = {"00.01-08.00 น.": 0, "08.01-16.00 น.": 0, "16.01-24.00 น.": 0}

    for row in data:
        type_ = row.get("vehicle_type", "ไม่ระบุ")
        model = row.get("model", "ไม่ระบุ").strip().upper()

        if type_ not in models_by_type:
            models_by_type[type_] = {}
        models_by_type[type_][model] = models_by_type[type_].get(model, 0) + 1

        t = row.get("time_reported")
        if t:
            h = int(str(t).split(":")[0])
            if 0 <= h <= 8:
                time_ranges["00.01-08.00 น."] += 1
            elif 8 < h <= 16:
                time_ranges["08.01-16.00 น."] += 1
            else:
                time_ranges["16.01-24.00 น."] += 1

    return {
        "models_by_type": models_by_type,
        "time_ranges": time_ranges
    }


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
    import json

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

    for item in items:
        raw = item.get("image_urls")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            parsed = raw

        if isinstance(parsed, list):
            image_urls = parsed
        elif isinstance(parsed, str):
            image_urls = [parsed]
        else:
            image_urls = []

        item["files"] = [{"file_url": url} for url in image_urls]

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
#แก้ 3