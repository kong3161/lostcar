
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from supabase import create_client
from uuid import uuid4
from urllib.parse import quote
import os
from datetime import datetime

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(url, key)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

@app.post("/submit")
async def handle_form(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
    files: list[UploadFile] = File(None)
):
    try:
        result = supabase.table("reports").insert({
            "title": title,
            "description": description,
            "date": date,
            "location": location,
            "uploaded_at": datetime.utcnow().isoformat()
        }).execute()

        report_id = result.data[0]["id"]
        print("[DEBUG] Report inserted with ID:", report_id)

        if files:
            for file in files:
                print("[DEBUG] Processing file:", file.filename)
                contents = await file.read()
                try:
                    filename = f"{uuid4()}_{file.filename}"
                    safe_filename = quote(filename)
                    print("[DEBUG] Uploading to Supabase:", safe_filename)
                    supabase.storage.from_("uploads").upload(safe_filename, contents, {"content-type": file.content_type})
                except Exception as upload_err:
                    return JSONResponse(status_code=500, content={"error": f"File upload failed: {upload_err}"})

                public_url = f"{url}/storage/v1/object/public/uploads/{safe_filename}"
                print("[DEBUG] Public URL created:", public_url)
                supabase.table("file_urls").insert({
                    "report_id": report_id,
                    "file_url": public_url
                }).execute()

        return templates.TemplateResponse("form.html", {
            "request": request,
            "message": "✅ บันทึกข้อมูลเรียบร้อยแล้ว"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
