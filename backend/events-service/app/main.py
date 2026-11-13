import json
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers import router

app = FastAPI(title="events-service")
app.include_router(router)


@app.middleware("http")
async def bitacora(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    log = {
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
        "correlation_id": correlation_id,
    }
    print(json.dumps(log), flush=True)

    response.headers["X-Correlation-Id"] = correlation_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"detail": "invalid body"})
