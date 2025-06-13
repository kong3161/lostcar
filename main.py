
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
    # Convert date/time fields to ISO format for Supabase
    try:
        date_lost_parsed = datetime.strptime(date_lost, "%d/%m/%Y").date().isoformat()
    except ValueError:
        date_lost_parsed = None

    try:
        time_event_parsed = datetime.strptime(time_event, "%H:%M").time().isoformat()
    except ValueError:
        time_event_parsed = None

    try:
        time_reported_parsed = datetime.strptime(time_reported, "%H:%M").time().isoformat()
    except ValueError:
        time_reported_parsed = None

    uploaded_at = datetime.utcnow().isoformat()

    data = {
        "vehicle_type": vehicle_type,
        "brand": brand,
        "model": model,
        "date_lost": date_lost_parsed,
        "time_event": time_event_parsed,
        "time_reported": time_reported_parsed,
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

    message = (
        f"<b>ผลลัพธ์จาก Supabase</b><br>"
        f"<b>Status:</b> {response.status_code}<br>"
        f"<b>ส่งข้อมูล:</b> {data}<br>"
        f"<b>คำตอบ:</b> {response.text}"
    )

    return HTMLResponse(content=message, status_code=200)

from search_router import router as search_router
app.include_router(search_router)
