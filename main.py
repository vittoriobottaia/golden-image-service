from typing import Optional

from fastapi import FastAPI, File, Query, UploadFile
from fastapi.responses import StreamingResponse

from services.image_service import ImageProcessingError, ImageService
from utils.responses import error_response

app = FastAPI(title="Golden Media API", version="1.0.0")
image_service = ImageService()


@app.get("/")
def root() -> dict:
    return image_service.build_root_payload()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": image_service.service_name,
    }


@app.post("/heic-to-jpg")
async def heic_to_jpg(file: UploadFile = File(...)) -> StreamingResponse:
    try:
        return await image_service.convert_to_jpg(file)
    except ImageProcessingError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        return error_response(f"Unexpected processing error: {exc}", status_code=500)


@app.post("/convert-to-jpg")
async def convert_to_jpg(file: UploadFile = File(...)) -> StreamingResponse:
    try:
        return await image_service.convert_to_jpg(file)
    except ImageProcessingError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        return error_response(f"Unexpected processing error: {exc}", status_code=500)


@app.post("/resize")
async def resize_image(
    file: UploadFile = File(...),
    width: Optional[int] = Query(default=None, ge=1),
    height: Optional[int] = Query(default=None, ge=1),
    keep_aspect_ratio: bool = True,
    quality: int = Query(default=90, ge=1, le=100),
) -> StreamingResponse:
    try:
        return await image_service.resize_image(
            file=file,
            width=width,
            height=height,
            keep_aspect_ratio=keep_aspect_ratio,
            quality=quality,
        )
    except ImageProcessingError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        return error_response(f"Unexpected processing error: {exc}", status_code=500)


@app.post("/compress")
async def compress_image(
    file: UploadFile = File(...),
    quality: int = Query(default=85, ge=1, le=100),
) -> StreamingResponse:
    try:
        return await image_service.compress_image(file=file, quality=quality)
    except ImageProcessingError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        return error_response(f"Unexpected processing error: {exc}", status_code=500)


@app.post("/thumbnail")
async def thumbnail(
    file: UploadFile = File(...),
    size: int = Query(default=512, ge=1),
) -> StreamingResponse:
    try:
        return await image_service.create_thumbnail(file=file, size=size)
    except ImageProcessingError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        return error_response(f"Unexpected processing error: {exc}", status_code=500)


@app.post("/instagram-feed")
async def instagram_feed(
    file: UploadFile = File(...),
    blur_background: bool = True,
    background_color: Optional[str] = Query(default=None),
    quality: int = Query(default=92, ge=1, le=100),
) -> StreamingResponse:
    try:
        return await image_service.create_instagram_feed(
            file=file,
            blur_background=blur_background,
            background_color=background_color,
            quality=quality,
        )
    except ImageProcessingError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        return error_response(f"Unexpected processing error: {exc}", status_code=500)


@app.post("/instagram-story")
async def instagram_story(
    file: UploadFile = File(...),
    blur_background: bool = True,
    background_color: Optional[str] = Query(default=None),
    quality: int = Query(default=92, ge=1, le=100),
) -> StreamingResponse:
    try:
        return await image_service.create_instagram_story(
            file=file,
            blur_background=blur_background,
            background_color=background_color,
            quality=quality,
        )
    except ImageProcessingError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        return error_response(f"Unexpected processing error: {exc}", status_code=500)