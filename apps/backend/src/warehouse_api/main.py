from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from warehouse_api.audit_discrepancy_routes import router as audit_discrepancy_router
from warehouse_api.audit_routes import router as audit_router
from warehouse_api.auth_routes import router as auth_router
from warehouse_api.config import get_settings
from warehouse_api.errors import ApiError
from warehouse_api.pick_routes import router as pick_router
from warehouse_api.receive_routes import router as receive_router
from warehouse_api.routes import router
from warehouse_api.transfer_routes import router as transfer_router

app = FastAPI(
    title="Warehouse & Smart Inventory Management API",
    version="0.1.0",
)

settings = get_settings()


def _is_json_content_type(content_type: str) -> bool:
    media_type, _, _parameters = content_type.partition(";")
    return media_type.strip().lower() == "application/json"


@app.middleware("http")
async def enforce_cross_site_request_policy(request: Request, call_next):
    if settings.cookie_samesite == "none" and request.method in {
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    }:
        if request.headers.get("origin") not in settings.cors_origins:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "INVALID_ORIGIN",
                        "message": "The request origin is not allowed.",
                        "details": {},
                    }
                },
            )
        content_type = request.headers.get("content-type", "")
        if not _is_json_content_type(content_type):
            return JSONResponse(
                status_code=415,
                content={
                    "error": {
                        "code": "UNSUPPORTED_MEDIA_TYPE",
                        "message": "Mutation requests must use application/json.",
                        "details": {},
                    }
                },
            )
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)
app.include_router(auth_router)
app.include_router(router)
app.include_router(receive_router)
app.include_router(pick_router)
app.include_router(transfer_router)
app.include_router(audit_router)
app.include_router(audit_discrepancy_router)


@app.exception_handler(ApiError)
def handle_api_error(_request: Request, error: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
def handle_validation_error(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    recheck_quantity_error = any(
        item["loc"][-1] == "recheck_physical_quantity" for item in error.errors()
    )
    quantity_error = any(
        item["loc"][-1] == "physical_quantity"
        or (
            item["loc"][-1] in {"quantity", "actual_quantity"}
            and (item["type"] != "missing" or request.url.path == "/api/v1/transfers")
        )
        for item in error.errors()
    )
    allocations_error = any("allocations" in item["loc"] for item in error.errors())
    if recheck_quantity_error:
        code = "INVALID_RECHECK_QUANTITY"
        message = "Recheck physical quantity must be an integer from 0 to 2147483647."
    elif quantity_error:
        code = "INVALID_QUANTITY"
        message = "Quantity must be an integer."
    elif allocations_error:
        code = "INVALID_ALLOCATIONS"
        message = "The source allocations are invalid."
    else:
        code = "INVALID_REQUEST"
        message = "The request could not be validated."
    return JSONResponse(
        status_code=422,
        content={
            "error": {"code": code, "message": message, "details": error.errors()}
        },
    )


@app.get("/health", tags=["technical"])
def health() -> dict[str, str]:
    return {"status": "ok"}
