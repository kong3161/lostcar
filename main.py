import os
import json
from io import BytesIO
from math import ceil
from datetime import datetime
from urllib.parse import urlencode, quote

import httpx
from dotenv import load_dotenv
from openpyxl import Workbook
import cloudinary
import cloudinary.uploader

from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Body

from supabase import create_client

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

# -------------------- เพิ่ม endpoint ฟอร์มและ export excel --------------------
# ฟอร์มเลือกช่วงวันที่สำหรับรายงาน
@app.get("/report", response_class=HTMLResponse)
async def report_form(request: Request):
    return templates.TemplateResponse("report.html", {"request": request})

# สร้างไฟล์ Excel รายงานรถหายตามช่วงวันที่
@app.get("/export")
async def export_excel(from_date: str, to_date: str):
    try:
        from_dt = datetime.fromisoformat(from_date).date()
        to_dt = datetime.fromisoformat(to_date).date()
        if from_dt > to_dt:
            from_dt, to_dt = to_dt, from_dt
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "รูปแบบวันที่ไม่ถูกต้อง"})

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    result = supabase.table("reports")\
        .select("*")\
        .gte("date_lost", from_dt.isoformat())\
        .lte("date_lost", to_dt.isoformat())\
        .execute()
    data = result.data if result.data else []

    wb = Workbook()
    ws = wb.active
    ws.title = "รายงานรถหาย"
    headers = ["ID", "ประเภทรถ", "ยี่ห้อ", "รุ่น", "สี", "วันที่หาย", "ผู้แจ้ง", "ละติจูด", "ลองจิจูด" , "รายละเอียด" , "สถานที่หาย" , "เขต"]
    ws.append(headers)

    for row in data:
        ws.append([
            row.get("id"),
            row.get("vehicle_type"),
            row.get("brand"),
            row.get("model"),
            row.get("color"),
            row.get("date_lost"),
            row.get("reporter"),
            row.get("lat"),
            row.get("lng"),
            row.get("details"),
            row.get("location"),
            row.get("zone"),
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"รายงานรถหาย_{from_date}_ถึง_{to_date}.xlsx"
    quoted = quote(filename)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"
        }
    )

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/submit", response_class=HTMLResponse)
async def form_page(request: Request):
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
    zone: str = Form(...),
    lat: str = Form(""),
    lng: str = Form(""),
    reporter: str = Form(""),
    details: str = Form(""),
    files: list[UploadFile] = File(None)
):
    from uuid import uuid4

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
                if file.filename:  # ✔ แนบไฟล์มาจริง
                    result = cloudinary.uploader.upload(file.file, resource_type="image")
                    uploaded_urls.append(result["secure_url"])

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
            "zone": zone,
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

        return templates.TemplateResponse("index.html", {"request": request, "success": True})

    except Exception as e:
        import traceback
        traceback.print_exc()
        print("❌ เกิดข้อผิดพลาด:", e)
        return templates.TemplateResponse("index.html", {"request": request, "error": True})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    from_date = request.query_params.get("from_date")
    to_date = request.query_params.get("to_date")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    query = supabase.table("reports").select("*")

    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date).date().isoformat()
            query = query.gte("date_lost", from_dt)
        except ValueError:
            pass

    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date).date().isoformat()
            query = query.lte("date_lost", to_dt)
        except ValueError:
            pass

    result = query.execute()
    rows = result.data if result.data else []

    zone_mapping = {
        "1": "เขตตรวจที่ 1",
        "2": "เขตตรวจที่ 2",
        "3": "เขตตรวจที่ 3",
        "4": "เขตตรวจที่ 4"
    }

    zone_counts = {}
    for row in rows:
        raw_zone = str(row.get("zone")).strip()
        name = zone_mapping.get(raw_zone)
        if name:
            zone_counts[name] = zone_counts.get(name, 0) + 1

    all_zones = ["เขตตรวจที่ 1", "เขตตรวจที่ 2", "เขตตรวจที่ 3", "เขตตรวจที่ 4"]
    ordered_counts = {zone: zone_counts.get(zone, 0) for zone in all_zones}

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "zone_counts": ordered_counts,
        "query_params": request.query_params
    })


@app.get("/dashboard-data")
async def dashboard_data(request: Request, from_date: str = None, to_date: str = None):
    """Return dashboard data filtered by optional from_date/to_date.
    Response JSON includes: zone_counts, models_by_type, time_ranges, total_recovered.
    """
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Normalize and build inclusive to_date when user supplies YYYY-MM-DD
        q = request.query_params
        fd = q.get("from_date") or from_date
        td = q.get("to_date") or to_date
        if fd and len(fd) == 10:
            # keep as date string YYYY-MM-DD
            from_filter = fd
        else:
            from_filter = fd
        if td and len(td) == 10:
            to_filter = td + "T23:59:59"
        else:
            to_filter = td

        # Build supabase query (select needed columns)
        base = supabase.table("reports").select("id,zone,is_recovered,model,brand,vehicle_type,time_reported,date_lost")
        if from_filter:
            base = base.gte("date_lost", from_filter)
        if to_filter:
            base = base.lte("date_lost", to_filter)

        resp = base.execute()
        rows = getattr(resp, "data", None) or []

        # zone_counts and total_recovered
        zone_counts = {}
        total_recovered = 0
        for r in rows:
            z = r.get("zone") or "(ไม่มีเขต)"
            zone_counts[z] = zone_counts.get(z, 0) + 1
            v = r.get("is_recovered")
            if v is True or v == 1 or str(v).lower() == "true":
                total_recovered += 1

        # models_by_type aggregation
        models_by_type = {}
        for r in rows:
            ttype = r.get("vehicle_type") or r.get("brand") or "อื่นๆ"
            model = (r.get("model") or "ไม่ระบุ").strip()
            models_by_type.setdefault(ttype, {})
            models_by_type[ttype][model] = models_by_type[ttype].get(model, 0) + 1

        # time_ranges buckets
        time_ranges = {"00.01-08.00 น.": 0, "08.01-16.00 น.": 0, "16.01-24.00 น.": 0}
        for r in rows:
            t = r.get("time_reported") or r.get("date_lost")
            if not t:
                continue
            try:
                hour = None
                if isinstance(t, str) and "T" in t:
                    hour = int(t.split("T")[1].split(":")[0])
                elif isinstance(t, str) and " " in t:
                    hour = int(t.split(" ")[1].split(":")[0])
                else:
                    hour = int(str(t).split(":")[0])
                if hour is None:
                    continue
                if 0 <= hour <= 8:
                    time_ranges["00.01-08.00 น."] += 1
                elif 8 < hour <= 16:
                    time_ranges["08.01-16.00 น."] += 1
                else:
                    time_ranges["16.01-24.00 น."] += 1
            except Exception:
                continue

        result = {
            "zone_counts": zone_counts,
            "models_by_type": models_by_type,
            "time_ranges": time_ranges,
            "total_recovered": total_recovered
        }
        return JSONResponse(content=result)

    except Exception as e:
        print("Error in /dashboard-data:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})

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
    date_lost_from: str = "",
    date_lost_to: str = "",
    reporter: str = "",
    color: str = "",
    plate_prefix: str = "",
    plate_number: str = "",
    plate_province: str = "",
    engine_number: str = "",
    chassis_number: str = "",
    zone: str = "",
):
    limit = 5
    offset = (page - 1) * limit

    filter_parts = []
    if vehicle_type:
        filter_parts.append(f"vehicle_type=eq.{vehicle_type}")
    if brand:
        filter_parts.append(f"brand=ilike.*{brand}*")
    if model:
        filter_parts.append(f"model=ilike.*{model}*")

    if date_lost_from or date_lost_to:
        filter_parts.append("date_lost=not.is.null")
        if date_lost_from and date_lost_to:
            try:
                from_date = datetime.fromisoformat(date_lost_from)
                to_date = datetime.fromisoformat(date_lost_to)
                if from_date <= to_date:
                    filter_parts.append(f"date_lost=gte.{date_lost_from}")
                    filter_parts.append(f"date_lost=lte.{date_lost_to}")
                else:
                    # สลับลำดับหากผู้ใช้กรอกกลับด้าน
                    filter_parts.append(f"date_lost=gte.{date_lost_to}")
                    filter_parts.append(f"date_lost=lte.{date_lost_from}")
            except ValueError:
                pass
        elif date_lost_from:
            filter_parts.append(f"date_lost=gte.{date_lost_from}")
        elif date_lost_to:
            filter_parts.append(f"date_lost=lte.{date_lost_to}")

    if reporter:
        filter_parts.append(f"reporter=ilike.*{reporter}*")
    if color:
        filter_parts.append(f"color=ilike.*{color}*")
    if plate_prefix:
        filter_parts.append(f"plate_prefix=ilike.*{plate_prefix}*")
    if plate_number:
        filter_parts.append(f"plate_number=ilike.*{plate_number}*")
    if plate_province:
        filter_parts.append(f"plate_province=ilike.*{plate_province}*")
    if engine_number:
        filter_parts.append(f"engine_number=ilike.*{engine_number}*")
    if chassis_number:
        filter_parts.append(f"chassis_number=ilike.*{chassis_number}*")
    if zone:
        filter_parts.append(f"zone=eq.{zone}")

    filter_query = "&".join(filter_parts)
    base_url = f"{SUPABASE_URL}/rest/v1/reports"
    url = f"{base_url}?{filter_query}&order=date_lost.desc&limit={limit}&offset={offset}" if filter_query else f"{base_url}?order=date_lost.desc&limit={limit}&offset={offset}"
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

    query_params_no_page = request.query_params.multi_items()
    query_params_filtered = [(k, v) for k, v in query_params_no_page if k != "page"]
    query_string = "&".join(f"{k}={v}" for k, v in query_params_filtered)

    return templates.TemplateResponse("results.html", {
        "request": request,
        "items": items,
        "debug_url": url,
        "debug_status": response.status_code,
        "debug_raw": response.text,
        "page": page,
        "total_pages": total_pages,
        "zone": zone,
        "vehicle_type": vehicle_type,
        "brand": brand,
        "model": model,
        "date_lost_from": date_lost_from,
        "date_lost_to": date_lost_to,
        "reporter": reporter,
        "color": color,
        "plate_prefix": plate_prefix,
        "plate_number": plate_number,
        "plate_province": plate_province,
        "engine_number": engine_number,
        "chassis_number": chassis_number,
        "query_string": query_string,
    })

# เพิ่ม endpoint สำหรับหน้าแผนที่
@app.get("/map", response_class=HTMLResponse)
async def show_map(request: Request, from_date: str = None, to_date: str = None):
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    query = supabase.table("reports").select("*").neq("lat", "0").neq("lng", "0")

    if from_date and to_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_dt > to_dt:
                from_dt, to_dt = to_dt, from_dt

            query = query.gte("date_lost", from_dt.isoformat()).lte("date_lost", to_dt.isoformat())
        except ValueError:
            pass  # ถ้าผู้ใช้กรอกวันที่ผิดฟอร์แมต ให้แสดงทั้งหมด

    response = query.execute()
    reports = response.data if response.data else []

    return templates.TemplateResponse("map.html", {
        "request": request,
        "reports": reports,
        "google_maps_api_key": os.getenv("GOOGLE_MAPS_API_KEY")
    })
    
    
@app.post("/update-status/{report_id}")
async def update_status(report_id: int, request: Request):
    """
    Accept either JSON body { "status": true } or form-encoded/body with field 'status'.
    This endpoint will update the boolean column `is_recovered` for the given report id.
    It is resilient to different content types and will coerce common truthy string values.
    """
    try:
        # Try to parse JSON body first
        try:
            payload = await request.json()
        except Exception:
            # Fallback to form body
            form = await request.form()
            payload = dict(form)

        # Accept multiple possible keys for compatibility
        raw_status = None
        if isinstance(payload, dict):
            for key in ("status", "is_recovered", "found"):
                if key in payload:
                    raw_status = payload.get(key)
                    break

        # Normalize status to boolean
        if isinstance(raw_status, str):
            raw_status_val = raw_status.strip().lower()
            status = raw_status_val in ("1", "true", "yes", "on")
        else:
            status = bool(raw_status)

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = supabase.table("reports").update({"is_recovered": status}).eq("id", report_id).execute()
        return JSONResponse(content={"success": True, "data": getattr(result, "data", None)})
    except Exception as e:
        print("Error updating status:", e)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})