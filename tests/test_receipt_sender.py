from datetime import datetime, timezone
from typing import Any

from course_receipts.models import CourseDelivery, ReceiptRequest
from course_receipts.receipt_sender import send_course_receipt


class RecordingEmail:
    def __init__(self) -> None:
        self.call: dict[str, Any] = {}

    def send(self, **kwargs: Any) -> dict[str, str]:
        self.call = kwargs
        return {"message_id": "msg_course_1042"}


def test_receipt_marks_late_educator_report_and_keeps_delivery_context() -> None:
    email = RecordingEmail()
    request = ReceiptRequest(
        order_id="ORDER-1042",
        learner_name="Maya Chen",
        learner_email="maya@example.com",
        amount="49.00",
        currency="USD",
        delivery=CourseDelivery(
            course_title="Practical SQL",
            access_url="https://learn.example.test/sql",
            learner_deadline=datetime(2026, 8, 20, tzinfo=timezone.utc),
            educator_report_due=datetime(2026, 8, 15, tzinfo=timezone.utc),
        ),
    )

    result = send_course_receipt(
        request,
        email,  # type: ignore[arg-type]
        now=datetime(2026, 8, 16, tzinfo=timezone.utc),
    )

    assert result.reporting_state == "overdue"
    assert result.message_id == "msg_course_1042"
    assert email.call["idempotency_key"] == "course-receipt:ORDER-1042"
    assert "Learner deadline: 2026-08-20T00:00:00+00:00" in email.call["html"]
    assert "Educator report due: 2026-08-15T00:00:00+00:00 (overdue)" in email.call["html"]

