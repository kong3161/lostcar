
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import httpx
from datetime import datetime
from urllib.parse import urlencode

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SUPABASE_URL = "https://ntxrmhzrxorufzjvejch.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im50eHJtaHpyeG9ydWZ6anZlamNoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk3OTI2NDUsImV4cCI6MjA2NTM2ODY0NX0.xS0LA1ZGVZ_Lq0E-QjTyYCS9NHy5m4t0jbeDvXpKuSE"
HEADERS = {"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {SUPABASE_ANON_KEY}"}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

@app.get("/results", response_class=HTMLResponse)
async def results(request: Request,
                  vehicle_type: str = "", brand: str = "", model: str = "", date_lost: str = "",
                  reporter: str = "", color: str = "", plate_number: str = "",
                  engine_number: str = "", chassis_number: str = "", page: int = 1):

    params = {"order": "uploaded_at.desc"}
    filters = []

    def append_filter(key, value):
        if value:
            filters.append(f"{key}.eq.{value}")

    append_filter("vehicle_type", vehicle_type)
    append_filter("brand", brand)
    append_filter("model", model)
    append_filter("date_lost", date_lost)
    append_filter("reporter", reporter)
    append_filter("color", color)
    append_filter("plate_number", plate_number)
    append_filter("engine_number", engine_number)
    append_filter("chassis_number", chassis_number)

    if filters:
        params["or"] = "(" + ",".join(filters) + ")"

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{SUPABASE_URL}/rest/v1/reports", headers=HEADERS, params=params)
        all_results = r.json()

    per_page = 5
    total = len(all_results)
    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    results = all_results[start:start+per_page]

    query_params = request.query_params.multi_items()
    query = urlencode([(k, v) for k, v in query_params if k != "page"])

    return templates.TemplateResponse("results.html", {
        "debug_url": debug_url,
        "debug_status": response.status_code,
        "debug_raw": response.text,
        "request": request,
        "results": results,
        "page": page,
        "total_pages": total_pages,
        "query": query
    })

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard-data")
async def dashboard_data():
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{SUPABASE_URL}/rest/v1/reports?select=vehicle_type,model,time_reported", headers=HEADERS)
        rows = res.json()

    from collections import defaultdict
    from datetime import time

    models_by_type = defaultdict(lambda: defaultdict(int))
    time_ranges = {"เช้า": 0, "กลางวัน": 0, "กลางคืน": 0}

    for row in rows:
        vtype = row["vehicle_type"] or "ไม่ระบุ"
        model = (row["model"] or "").strip().lower()
        if model:
            models_by_type[vtype][model] += 1

        t = row.get("time_reported")
        if t:
            hour = int(t.split(":")[0])
            if 5 <= hour < 12:
                time_ranges["เช้า"] += 1
            elif 12 <= hour < 18:
                time_ranges["กลางวัน"] += 1
            else:
                time_ranges["กลางคืน"] += 1

    return {"models_by_type": models_by_type, "time_ranges": time_ranges}

@app.post("/submit")
async def submit(request: Request,
                 vehicle_type: str = Form(...),
                 brand: str = Form(...),
                 model: str = Form(...),
                 color: str = Form(""),
                 plate_prefix: str = Form(""),
                 plate_number: str = Form(""),
                 plate_province: str = Form(""),
                 engine_number: str = Form(""),
                 chassis_number: str = Form(""),
                 date_lost: str = Form(...),
                 time_event: str = Form(...),
                 time_reported: str = Form(...),
                 location: str = Form(...),
                 lat: str = Form(...),
                 lng: str = Form(...),
                 reporter: str = Form(...),
                 details: str = Form(...),
                 files: list[UploadFile] = File(None)):

    metadata = {
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
        "uploaded_at": datetime.utcnow().isoformat()
    }

    async with httpx.AsyncClient() as client:
        await client.post(f"{SUPABASE_URL}/rest/v1/reports", headers={**HEADERS, "Content-Type": "application/json"}, json=metadata)

        if files:
            for file in files:
                contents = await file.read()
                filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
                await client.put(f"{SUPABASE_URL}/storage/v1/object/uploads/{filename}",
                                 headers={**HEADERS, "Content-Type": file.content_type},
                                 content=contents)
                await client.post(f"{SUPABASE_URL}/rest/v1/file_urls",
                                  headers={**HEADERS, "Content-Type": "application/json"},
                                  json={"file_name": file.filename, "file_path": f"uploads/{filename}"})

    return RedirectResponse("/", status_code=303)
