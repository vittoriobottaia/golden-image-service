from typing import Optional

from fastapi.responses import JSONResponse


def success_response(message: str, data: Optional[dict] = None, status_code: int = 200) -> JSONResponse:
    payload = {"message": message}
    if data is not None:
        payload.update(data)
    return JSONResponse(status_code=status_code, content=payload)


def error_response(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})
