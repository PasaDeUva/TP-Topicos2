import json
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse


async def request_log(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        response = JSONResponse(
            status_code=500,
            content={"code": "internal_error", "message": "Internal server error"},
        )

    record = {
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round((time.perf_counter() - start) * 1000, 2),
        "correlation_id": correlation_id,
    }
    print(json.dumps(record), flush=True)
    response.headers["X-Correlation-Id"] = correlation_id
    return response
