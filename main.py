
from fastapi import FastAPI, Form, UploadFile, File, Request, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import httpx
from datetime import datetime
from urllib.parse import urlencode

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

@app.post("/submit", response_class=HTMLResponse)
async def handle_form(
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
    uploaded_at = datetime.utcnow().isoformat()
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
        "date_lost": date_lost,
        "time_event": time_event,
        "time_reported": time_reported,
        "location": location,
        "lat": lat,
        "lng": lng,
        "reporter": reporter,
        "details": details,
        "uploaded_at": uploaded_at
    }

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/reports",
            json=data,
            headers=headers
        )

    if response.status_code in [200, 201]:
        message = "ส่งข้อมูลเรียบร้อยแล้ว ✅"
    else:
        message = f"เกิดข้อผิดพลาด: {response.status_code} - {response.text}"

    return templates.TemplateResponse("submitted.html", {
        "request": request,
        "brand": brand,
        "model": model,
        "message": message
    })

@app.get("/dashboard-data")
async def dashboard_data():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/reports?select=vehicle_type,model,time_reported", headers=headers)

    if resp.status_code != 200:
        return JSONResponse(status_code=resp.status_code, content={"error": "Failed to fetch data"})

    rows = resp.json()
    models_by_type = {}
    time_ranges = {
        "00.01-08.00 น.": 0,
        "08.01-16.00 น.": 0,
        "16.01-24.00 น.": 0
    }

    for row in rows:
        vtype = row.get("vehicle_type") or "ไม่ระบุ"
        model = (row.get("model") or "ไม่ระบุ").strip().upper()

        if vtype not in models_by_type:
            models_by_type[vtype] = {}

        models_by_type[vtype][model] = models_by_type[vtype].get(model, 0) + 1

        time_str = row.get("time_reported")
        if time_str:
            try:
                h, m, *_ = map(int, time_str.split(":"))
                if 0 <= h <= 8:
                    time_ranges["00.01-08.00 น."] += 1
                elif 8 < h <= 16:
                    time_ranges["08.01-16.00 น."] += 1
                else:
                    time_ranges["16.01-24.00 น."] += 1
            except:
                pass

    return {
        "models_by_type": models_by_type,
        "time_ranges": time_ranges
    }
