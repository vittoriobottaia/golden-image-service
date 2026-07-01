from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from PIL import Image
import pillow_heif
import io

pillow_heif.register_heif_opener()

app = FastAPI(title="Golden Image Service")

@app.get("/")
def health():
    return {
        "status": "ok",
        "service": "Golden Image Service"
    }

@app.post("/heic-to-jpg")
async def heic_to_jpg(file: UploadFile = File(...)):
    try:
        input_bytes = await file.read()

        image = Image.open(io.BytesIO(input_bytes))

        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        output = io.BytesIO()

        image.save(
            output,
            format="JPEG",
            quality=92,
            optimize=True
        )

        output.seek(0)

        return StreamingResponse(
            output,
            media_type="image/jpeg",
            headers={
                "Content-Disposition":
                "attachment; filename=converted.jpg"
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e)
            }
        )