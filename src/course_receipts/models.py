from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class CourseDelivery(BaseModel):
    course_title: str = Field(min_length=1)
    access_url: str
    learner_deadline: datetime
    educator_report_due: datetime


class ReceiptRequest(BaseModel):
    order_id: str = Field(min_length=1)
    learner_name: str = Field(min_length=1)
    learner_email: EmailStr
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    delivery: CourseDelivery


class ReceiptResult(BaseModel):
    order_id: str
    message_id: str
    reporting_state: str

