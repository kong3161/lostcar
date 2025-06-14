
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import httpx
from datetime import datetime
from urllib.parse import urlencode, quote
from math import ceil
from uuid import uuid4
from supabase import create_client

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    try:
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
            "uploaded_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("reports").insert(data).execute()
        report_id = result.data[0]["id"]

        if files:
            for file in files:
                contents = await file.read()
                filename = f"{uuid4()}_{file.filename}"
                safe_filename = quote(filename)
                supabase.storage.from_("uploads").upload(safe_filename, contents, {
                    "content-type": file.content_type
                })
                public_url = f"{SUPABASE_URL}/storage/v1/object/public/uploads/{safe_filename}"
                supabase.table("file_urls").insert({
                    "report_id": report_id,
                    "file_url": public_url,
                    "file_name": file.filename
                }).execute()

        return templates.TemplateResponse("index.html", {
            "request": request,
            "message": "✅ บันทึกข้อมูลเรียบร้อยแล้ว"
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
