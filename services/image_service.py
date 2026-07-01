import io
import os
from typing import Optional

from fastapi import UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError
import pillow_heif

pillow_heif.register_heif_opener()


class ImageProcessingError(Exception):
    """Raised when an uploaded image cannot be processed."""


class ImageService:
    MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

    def __init__(self) -> None:
        self.service_name = "Golden Media API"
        self.version = "1.0.0"

    def build_root_payload(self) -> dict:
        return {
            "status": "ok",
            "service": self.service_name,
            "version": self.version,
            "endpoints": [
                {"path": "/", "method": "GET", "description": "API information"},
                {"path": "/health", "method": "GET", "description": "Health check"},
                {"path": "/heic-to-jpg", "method": "POST", "description": "Convert HEIC/HEIF to JPG"},
                {"path": "/convert-to-jpg", "method": "POST", "description": "Convert any Pillow-supported image to JPG"},
                {"path": "/resize", "method": "POST", "description": "Resize image to requested dimensions"},
                {"path": "/compress", "method": "POST", "description": "Compress image JPEG quality"},
                {"path": "/thumbnail", "method": "POST", "description": "Create a square or proportional thumbnail"},
                {"path": "/instagram-feed", "method": "POST", "description": "Create Instagram feed sized image"},
                {"path": "/instagram-story", "method": "POST", "description": "Create Instagram story sized image"},
            ],
        }

    async def read_upload(self, file: UploadFile) -> bytes:
        if not file or not file.filename:
            raise ImageProcessingError("No file provided")

        if file.content_type and not file.content_type.startswith("image/"):
            raise ImageProcessingError("Uploaded file is not an image")

        data = await file.read()
        if not data:
            raise ImageProcessingError("Uploaded file is empty")
        if len(data) > self.MAX_FILE_SIZE_BYTES:
            raise ImageProcessingError("Uploaded file exceeds the 25 MB limit")
        return data

    def open_image(self, data: bytes) -> Image.Image:
        try:
            image = Image.open(io.BytesIO(data))
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ImageProcessingError("Uploaded file is not a valid image") from exc

        image = ImageOps.exif_transpose(image)
        image.load()
        return image

    def ensure_rgb(self, image: Image.Image) -> Image.Image:
        if image.mode in {"RGBA", "LA", "P"}:
            alpha_image = image.convert("RGBA")
            background = Image.new("RGBA", alpha_image.size, "white")
            background.alpha_composite(alpha_image)
            return background.convert("RGB")

        if image.mode not in {"RGB", "L", "CMYK", "YCbCr"}:
            return image.convert("RGB")
        if image.mode != "RGB":
            return image.convert("RGB")
        return image

    def create_response(self, image: Image.Image, filename: str, quality: int = 92) -> StreamingResponse:
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=quality, optimize=True)
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f"attachment; filename={self.safe_filename(filename)}",
                "Cache-Control": "no-store",
            },
        )

    def safe_filename(self, filename: str) -> str:
        base, ext = os.path.splitext(filename or "image")
        safe_base = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in base)
        return f"{safe_base or 'image'}.jpg"

    def build_error_response(self, message: str, status_code: int = 400) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"error": message})

    async def convert_to_jpg(self, file: UploadFile) -> StreamingResponse:
        data = await self.read_upload(file)
        image = self.open_image(data)
        image = self.ensure_rgb(image)
        return self.create_response(image, file.filename or "converted.jpg", quality=92)

    async def resize_image(
        self,
        file: UploadFile,
        width: Optional[int],
        height: Optional[int],
        keep_aspect_ratio: bool,
        quality: int,
    ) -> StreamingResponse:
        data = await self.read_upload(file)
        image = self.open_image(data)
        image = self.ensure_rgb(image)

        if width is None and height is None:
            raise ImageProcessingError("At least one of width or height must be provided")

        if width is not None and width <= 0:
            raise ImageProcessingError("width must be greater than 0")
        if height is not None and height <= 0:
            raise ImageProcessingError("height must be greater than 0")

        original_width, original_height = image.size
        if keep_aspect_ratio:
            if width is not None and height is None:
                ratio = width / original_width
                height = max(1, int(original_height * ratio))
            elif height is not None and width is None:
                ratio = height / original_height
                width = max(1, int(original_width * ratio))
            elif width is not None and height is not None:
                scale = min(width / original_width, height / original_height)
                width = max(1, int(original_width * scale))
                height = max(1, int(original_height * scale))
        else:
            if width is None:
                width = original_width
            if height is None:
                height = original_height

        resized = image.resize((width, height), Image.LANCZOS)
        return self.create_response(resized, file.filename or "resized.jpg", quality=quality)

    async def compress_image(self, file: UploadFile, quality: int) -> StreamingResponse:
        if not 1 <= quality <= 100:
            raise ImageProcessingError("quality must be between 1 and 100")

        data = await self.read_upload(file)
        image = self.open_image(data)
        image = self.ensure_rgb(image)
        return self.create_response(image, file.filename or "compressed.jpg", quality=quality)

    async def create_thumbnail(self, file: UploadFile, size: int) -> StreamingResponse:
        if size <= 0:
            raise ImageProcessingError("size must be greater than 0")

        data = await self.read_upload(file)
        image = self.open_image(data)
        image = self.ensure_rgb(image)

        image.thumbnail((size, size), Image.LANCZOS)
        return self.create_response(image, file.filename or "thumbnail.jpg", quality=92)

    async def create_instagram_feed(
        self,
        file: UploadFile,
        blur_background: bool = True,
        background_color: Optional[str] = None,
        quality: int = 92,
    ) -> StreamingResponse:
        data = await self.read_upload(file)
        image = self.open_image(data)
        image = self.ensure_rgb(image)

        target_width, target_height = 1080, 1350
        resized = self._fit_with_background(
            image,
            target_width,
            target_height,
            blur=blur_background,
            background_color=background_color,
        )
        return self.create_response(resized, file.filename or "instagram-feed.jpg", quality=quality)

    async def create_instagram_story(
        self,
        file: UploadFile,
        blur_background: bool = True,
        background_color: Optional[str] = None,
        quality: int = 92,
    ) -> StreamingResponse:
        data = await self.read_upload(file)
        image = self.open_image(data)
        image = self.ensure_rgb(image)

        target_width, target_height = 1080, 1920
        resized = self._fit_with_background(
            image,
            target_width,
            target_height,
            blur=blur_background,
            background_color=background_color,
        )
        return self.create_response(resized, file.filename or "instagram-story.jpg", quality=quality)

    def _fit_with_background(
        self,
        image: Image.Image,
        target_width: int,
        target_height: int,
        blur: bool,
        background_color: Optional[str] = None,
    ) -> Image.Image:
        original_width, original_height = image.size
        scale = min(target_width / original_width, target_height / original_height)
        new_width = max(1, int(original_width * scale))
        new_height = max(1, int(original_height * scale))

        main_image = image.resize((new_width, new_height), Image.LANCZOS)

        canvas_color = self._parse_background_color(background_color)
        canvas = Image.new("RGB", (target_width, target_height), color=canvas_color)

        if blur:
            background_source = image.copy()
            background_cover = background_source.resize(
                self._cover_size(background_source.size, (target_width, target_height)),
                Image.LANCZOS,
            )
            background_cover = background_cover.filter(ImageFilter.GaussianBlur(radius=10))
            canvas.paste(background_cover, (0, 0))
        else:
            canvas = Image.new("RGB", (target_width, target_height), color=canvas_color)

        offset_x = (target_width - new_width) // 2
        offset_y = (target_height - new_height) // 2
        canvas.paste(main_image, (offset_x, offset_y))
        return canvas

    def _cover_size(self, source_size: tuple[int, int], target_size: tuple[int, int]) -> tuple[int, int]:
        source_width, source_height = source_size
        target_width, target_height = target_size
        scale = max(target_width / source_width, target_height / source_height)
        return (max(1, int(source_width * scale)), max(1, int(source_height * scale)))

    def _parse_background_color(self, background_color: Optional[str]) -> tuple[int, int, int]:
        if not background_color:
            return (240, 240, 240)
        color_value = background_color.strip().lstrip("#")
        if len(color_value) == 3:
            color_value = "".join(ch * 2 for ch in color_value)
        if len(color_value) == 6:
            try:
                return tuple(int(color_value[i:i + 2], 16) for i in (0, 2, 4))
            except ValueError:
                return (240, 240, 240)
        return (240, 240, 240)
