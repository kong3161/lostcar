
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse
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
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im50eHJtaHpyeG9ydWZ6anZlamNoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk3OTI2NDUsImV4cCI6MjA2NTM2ODY0NX0.xS0LA1ZGVZ_Lq0E-QjTyYCS9NHy5m4t0jbeDvXpKuSE"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

@app.get("/", response_class=HTMLResponse)
def form_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/submit")
async def submit_form(
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
    date_lost: str = Form(...),
    time_event: str = Form(...),
    time_reported: str = Form(...),
    location: str = Form(...),
    lat: str = Form(...),
    lng: str = Form(...),
    reporter: str = Form(...),
    details: str = Form(...),
    files: list[UploadFile] = File(None)
):
    payload = {
        "vehicle_type": vehicle_type,
        "brand": brand,
        "model": model,
        "color": color,
        "plate_prefix": plate_prefix,
        "plate_number": plate_number,
        "plate_province": plate_province,
        "engine_number": engine_number,
        "chassis_number": chassis_number,
        "date_lost": date_lost if date_lost else None,
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
        await client.post(f"{SUPABASE_URL}/rest/v1/reports", headers=HEADERS, json=payload)

    return templates.TemplateResponse("success.html", {"request": request})

@app.get("/search", response_class=HTMLResponse)
def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

@app.get("/results", response_class=HTMLResponse)
async def search_results(
    request: Request,
    vehicle_type: str = "",
    brand: str = "",
    model: str = "",
    date_lost: str = "",
    reporter: str = "",
    color: str = "",
    plate_number: str = "",
    engine_number: str = "",
    chassis_number: str = "",
    page: int = 1,
    per_page: int = 5,
):
    params = {
        "or": f"(vehicle_type.ilike.*{vehicle_type}*,brand.ilike.*{brand}*,model.ilike.*{model}*,date_lost.eq.{date_lost},reporter.ilike.*{reporter}*,color.ilike.*{color}*,plate_number.ilike.*{plate_number}*,engine_number.ilike.*{engine_number}*,chassis_number.ilike.*{chassis_number}*)",
        "order": "uploaded_at.desc"
    }
    start = (page - 1) * per_page
    end = start + per_page - 1

    headers = HEADERS.copy()
    headers["Range"] = f"items={start}-{end}"

    async with httpx.AsyncClient() as client:
        res = await client.get(f"{SUPABASE_URL}/rest/v1/reports", headers=headers, params=params)
        results = res.json()

    return templates.TemplateResponse("results.html", {
        "request": request,
        "results": results,
        "debug_url": res.url,
        "debug_status": res.status_code,
        "debug_raw": res.text,
        "page": page,
        "has_next": len(results) == per_page,
        "query_params": {k: v for k, v in request.query_params.items() if k != "page"},
    })

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard-data")
async def dashboard_data():
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{SUPABASE_URL}/rest/v1/reports?select=vehicle_type,model,time_reported", headers=HEADERS)
        rows = res.json()

    model_stats = {}
    time_stats = {"เช้า": 0, "บ่าย": 0, "กลางคืน": 0}
    for row in rows:
        vehicle_type = row.get("vehicle_type", "ไม่ระบุ")
        model = (row.get("model") or "ไม่ระบุ").strip().lower()
        model_stats.setdefault(vehicle_type, {})
        model_stats[vehicle_type][model] = model_stats[vehicle_type].get(model, 0) + 1

        tr = row.get("time_reported")
        if tr:
            hour = int(tr.split(":")[0])
            if 5 <= hour < 12:
                time_stats["เช้า"] += 1
            elif 12 <= hour < 18:
                time_stats["บ่าย"] += 1
            else:
                time_stats["กลางคืน"] += 1

    return {
        "models_by_type": model_stats,
        "time_ranges": time_stats
    }
