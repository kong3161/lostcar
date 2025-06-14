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