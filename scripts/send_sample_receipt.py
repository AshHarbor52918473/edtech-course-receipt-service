import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from course_receipts.infrai_email import InfraiEmail
from course_receipts.models import CourseDelivery, ReceiptRequest
from course_receipts.receipt_sender import send_course_receipt


recipient = os.environ.get("RECEIPT_TO")
if not recipient:
    raise RuntimeError("RECEIPT_TO is required")

request = ReceiptRequest(
    order_id="ORDER-1042",
    learner_name="Maya Chen",
    learner_email=recipient,
    amount="49.00",
    currency="USD",
    delivery=CourseDelivery(
        course_title="Practical SQL for Product Builders",
        access_url="https://learn.example.test/courses/sql-1042",
        learner_deadline=datetime(2026, 9, 30, 23, 59, tzinfo=timezone.utc),
        educator_report_due=datetime(2026, 10, 2, 17, 0, tzinfo=timezone.utc),
    ),
)
result = send_course_receipt(request, InfraiEmail())
print(f"sent order={result.order_id} message_id={result.message_id} reporting={result.reporting_state}")
