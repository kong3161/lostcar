
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import httpx
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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
    try:
        date_lost = datetime.strptime(date_lost, "%Y-%m-%d").date().isoformat()
    except Exception:
        date_lost = None
    try:
        time_event = datetime.strptime(time_event, "%H:%M").time().isoformat()
    except Exception:
        time_event = None
    try:
        time_reported = datetime.strptime(time_reported, "%H:%M").time().isoformat()
    except Exception:
        time_reported = None

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

    try:
        response.raise_for_status()
        message = "✅ บันทึกข้อมูลเรียบร้อยแล้ว"
    except httpx.HTTPStatusError:
        message = (
            f"❗ Supabase error:<br>"
            f"<b>Status:</b> {response.status_code}<br>"
            f"<b>Response:</b> {response.text}<br>"
            f"<b>Sent data:</b> {data}"
        )

    return templates.TemplateResponse("submitted.html", {
        "request": request,
        "brand": brand,
        "model": model,
        "message": message
    })
from search_router import router as search_router
app.include_router(search_router)
