from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
from supabase import create_client
from dotenv import load_dotenv
from typing import List
import cloudinary.uploader

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Lost Car Report API"}


@app.post("/reports/")
async def create_report(report: dict):
    # Logic to create a new report
    return {"message": "Report created", "report": report}


@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    # Logic to retrieve a report by ID
    return {"report_id": report_id, "status": "found"}


@app.post("/submit")
async def submit_form(
    request: Request,
    vehicle_type: str = Form(...),
    brand: str = Form(...),
    model: str = Form(...),
    color: str = Form(...),
    plate_number: str = Form(...),
    engine_number: str = Form(...),
    chassis_number: str = Form(...),
    date_lost: str = Form(...),
    reporter: str = Form(...),
    tel: str = Form(...),
    files: List[UploadFile] = File(None)
):
    data = {
        "vehicle_type": vehicle_type,
        "brand": brand,
        "model": model,
        "color": color,
        "plate_number": plate_number,
        "engine_number": engine_number,
        "chassis_number": chassis_number,
        "date_lost": date_lost,
        "reporter": reporter,
        "tel": tel
    }

    try:
        response = supabase.table("reports").insert(data).execute()
        report_id = response.data[0]["id"]

        image_urls = []

        if files:
            for file in files:
                contents = await file.read()
                result = cloudinary.uploader.upload(contents, folder=f"lostcar/{report_id}/")
                image_urls.append(result["secure_url"])

        # บันทึกลิงก์รูปภาพลงในตาราง reports (field: image_urls)
        if image_urls:
            image_urls_text = ",".join(image_urls)
            supabase.table("reports").update({"image_urls": image_urls_text}).eq("id", report_id).execute()

        return templates.TemplateResponse("success.html", {"request": request, "report_id": report_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/images/{report_id}", response_class=HTMLResponse)
async def view_images(request: Request, report_id: str):
    import cloudinary
    import cloudinary.api

    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True
    )

    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix=f"lostcar/{report_id}/",
            max_results=30
        )
        image_urls = [r["secure_url"] for r in result.get("resources", [])]
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    return templates.TemplateResponse("images.html", {
        "request": request,
        "image_urls": image_urls,
        "report_id": report_id
    })


# Dashboard route
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        response = supabase.table("reports").select("*").order("id", desc=True).execute()
        reports = response.data
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "reports": reports
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


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
    chassis_number: str = ""
):
    try:
        query = supabase.table("reports").select("*")

        if vehicle_type:
            query = query.ilike("vehicle_type", f"%{vehicle_type}%")
        if brand:
            query = query.ilike("brand", f"%{brand}%")
        if model:
            query = query.ilike("model", f"%{model}%")
        if date_lost:
            query = query.ilike("date_lost", f"%{date_lost}%")
        if reporter:
            query = query.ilike("reporter", f"%{reporter}%")
        if color:
            query = query.ilike("color", f"%{color}%")
        if plate_number:
            query = query.ilike("plate_number", f"%{plate_number}%")
        if engine_number:
            query = query.ilike("engine_number", f"%{engine_number}%")
        if chassis_number:
            query = query.ilike("chassis_number", f"%{chassis_number}%")

        results = query.execute().data

        return templates.TemplateResponse("results.html", {
            "request": request,
            "results": results
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})