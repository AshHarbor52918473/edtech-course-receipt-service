from datetime import datetime, timezone
from html import escape

from .infrai_email import InfraiEmail
from .models import ReceiptRequest, ReceiptResult


def reporting_state(deadline: datetime, now: datetime) -> str:
    comparable_deadline = deadline.astimezone(timezone.utc)
    comparable_now = now.astimezone(timezone.utc)
    return "overdue" if comparable_deadline < comparable_now else "scheduled"


def send_course_receipt(
    request: ReceiptRequest,
    email: InfraiEmail,
    now: datetime | None = None,
) -> ReceiptResult:
    clock = now or datetime.now(timezone.utc)
    state = reporting_state(request.delivery.educator_report_due, clock)
    amount = f"{request.amount:.2f} {request.currency.upper()}"
    html = (
        f"<h1>Receipt for {escape(request.delivery.course_title)}</h1>"
        f"<p>Hi {escape(request.learner_name)}, order "
        f"<strong>{escape(request.order_id)}</strong> is paid: {escape(amount)}.</p>"
        f"<p><a href=\"{escape(request.delivery.access_url, quote=True)}\">Open your course</a></p>"
        f"<p>Learner deadline: {request.delivery.learner_deadline.isoformat()}</p>"
        f"<p>Educator report due: {request.delivery.educator_report_due.isoformat()} "
        f"({state}).</p>"
    )
    data = email.send(
        to=str(request.learner_email),
        subject=f"Course receipt #{request.order_id}",
        html=html,
        idempotency_key=f"course-receipt:{request.order_id}",
    )
    return ReceiptResult(
        order_id=request.order_id,
        message_id=str(data["message_id"]),
        reporting_state=state,
    )

