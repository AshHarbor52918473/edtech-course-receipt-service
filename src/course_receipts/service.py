from fastapi import FastAPI, HTTPException

from .infrai_email import InfraiEmail, InfraiError
from .models import ReceiptRequest, ReceiptResult
from .receipt_sender import send_course_receipt

app = FastAPI(title="Course receipt service")


@app.post("/receipts", response_model=ReceiptResult, status_code=201)
def create_receipt(request: ReceiptRequest) -> ReceiptResult:
    try:
        return send_course_receipt(request, InfraiEmail())
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "message": exc.detail.get("message", exc.code)},
        ) from exc

