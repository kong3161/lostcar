
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

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
    files: list[UploadFile] = File(...)
):
    return templates.TemplateResponse("submitted.html", {"request": request, "brand": brand, "model": model})

