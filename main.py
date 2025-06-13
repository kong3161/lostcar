
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import httpx
from datetime import datetime

# Load Supabase credentials from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/submit", response_class=HTMLResponse)
async def submit(
    request: Request,
    vehicle_type: str = Form(...),
    brand: str = Form(...),
    model: str = Form(...),
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

    # Prepare data
    payload = {
        "vehicle_type": vehicle_type,
        "brand": brand,
        "model": model,
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
            json=payload,
            headers=headers
        )

    # Show detailed status
    try:
        response.raise_for_status()
        message = "✅ บันทึกข้อมูลเรียบร้อยแล้ว"
    except httpx.HTTPStatusError:
        message = (
            f"❗ เกิดข้อผิดพลาดในการเชื่อมต่อ Supabase:\n"
            f"Status: {response.status_code}\n"
            f"Details: {response.text}"
        )

    return templates.TemplateResponse("submitted.html", {
        "request": request,
        "brand": brand,
        "model": model,
        "message": message
    })
