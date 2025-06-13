
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import httpx
from datetime import datetime
from urllib.parse import urlencode

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
        response = await client.post(f"{SUPABASE_URL}/rest/v1/reports", json=data, headers=headers)
    message = "ส่งข้อมูลเรียบร้อยแล้ว ✅" if response.status_code in [200, 201] else f"เกิดข้อผิดพลาด: {response.status_code} - {response.text}"
    return templates.TemplateResponse("submitted.html", {"request": request, "brand": brand, "model": model, "message": message})

@app.get("/search", response_class=HTMLResponse)
async def search_form(request: Request):
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
    page: int = 1
):
    PAGE_SIZE = 5
    offset = (page - 1) * PAGE_SIZE
    or_conditions = []
    if vehicle_type: or_conditions.append(f"vehicle_type.eq.{vehicle_type}")
    if brand: or_conditions.append(f"brand.ilike.*{brand}*")
    if model: or_conditions.append(f"model.ilike.*{model}*")
    if date_lost: or_conditions.append(f"date_lost.eq.{date_lost}")
    if reporter: or_conditions.append(f"reporter.ilike.*{reporter}*")
    if color: or_conditions.append(f"color.ilike.*{color}*")
    if plate_number: or_conditions.append(f"plate_number.ilike.*{plate_number}*")
    if engine_number: or_conditions.append(f"engine_number.ilike.*{engine_number}*")
    if chassis_number: or_conditions.append(f"chassis_number.ilike.*{chassis_number}*")
    query = f"or=({','.join(or_conditions)})&order=uploaded_at.desc&limit={PAGE_SIZE}&offset={offset}" if or_conditions else f"order=uploaded_at.desc&limit={PAGE_SIZE}&offset={offset}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    async with httpx.AsyncClient() as client:
        res_data = await client.get(f"{SUPABASE_URL}/rest/v1/reports?{query}", headers=headers)
        results = res_data.json() if res_data.status_code == 200 else []
        count_query = f"{SUPABASE_URL}/rest/v1/reports?select=id"
        if or_conditions:
            count_query += f"&or=({','.join(or_conditions)})"
        res_count = await client.get(count_query, headers={**headers, "Range": "0-99999"})
        content_range = res_count.headers.get("Content-Range", "0/0")
        try:
            total = int(content_range.split("/")[-1])
        except:
            total = 0
        total_pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    base_params = request.query_params.multi_items()
    base_params = [(k, v) for k, v in base_params if k != "page"]
    base_url = "/results?" + urlencode(base_params)
    return templates.TemplateResponse("results.html", {
        "request": request,
        "results": results,
        "page": page,
        "total_pages": total_pages,
        "base_url": base_url
    })

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
        res = await client.get(f"{SUPABASE_URL}/rest/v1/reports?select=vehicle_type,model,time_reported", headers=headers)
        data = res.json() if res.status_code == 200 else []
    models_by_type = {}
    time_ranges = {"00.01-08.00": 0, "08.01-16.00": 0, "16.01-24.00": 0}
    for item in data:
        vehicle_type = item.get("vehicle_type") or "ไม่ระบุประเภท"
        model = item.get("model") or "ไม่ระบุรุ่น"
        models_by_type.setdefault(vehicle_type, {})
        models_by_type[vehicle_type][model] = models_by_type[vehicle_type].get(model, 0) + 1
        time_str = item.get("time_reported")
        if time_str:
            hour, minute, *_ = map(int, time_str.split(":"))
            total_minutes = hour * 60 + minute
            if total_minutes < 480:
                time_ranges["00.01-08.00"] += 1
            elif total_minutes <= 960:
                time_ranges["08.01-16.00"] += 1
            else:
                time_ranges["16.01-24.00"] += 1
    for t in models_by_type:
        sorted_items = sorted(models_by_type[t].items(), key=lambda x: x[1], reverse=True)
        models_by_type[t] = dict(sorted_items)
    return {"models_by_type": models_by_type, "time_ranges": time_ranges}
