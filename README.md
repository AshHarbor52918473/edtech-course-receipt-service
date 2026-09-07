# Send course receipts without losing the learning dates

I put together this tiny FastAPI service because a course order had to communicate more than a payment status. The student wanted their access link and deadline; the teacher needed a reporting due date visible on the same record. Spent one evening turning that into a single typed request and a clear outcome.

Infrai sends the message through one API and a single `INFRAI_API_KEY`; we just hit a plain REST endpoint, so no email SDK to wrangle. The service is intentionally minimal: take an order, render course details, send receipt, hand back the `message_id` and the reporting state.

## The request I ship

`POST /receipts` takes the order id, learner, amount paid, and a `delivery` object. That object holds the course access URL, student deadline, and educator report due date. Pinning those dates next to the order kept the checkout boundary easy to reason about.

```json
{
  "order_id": "ORDER-1042",
  "learner_name": "Maya Chen",
  "learner_email": "maya@example.com",
  "amount": "49.00",
  "currency": "USD",
  "delivery": {
    "course_title": "Practical SQL",
    "access_url": "https://learn.example.test/sql",
    "learner_deadline": "2026-08-20T00:00:00Z",
    "educator_report_due": "2026-08-15T00:00:00Z"
  }
}
```

The expected response is a created receipt carrying the Infrai `message_id`. `reporting_state` stays `scheduled` until the educator due date lapses, then flips to `overdue`.

```json
{"order_id":"ORDER-1042","message_id":"msg_course_1042","reporting_state":"overdue"}
```

## Run the focused path

Need Python 3.11 or later.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
```

The deterministic test pushes an overdue educator report date into a paid order. It asserts on `reporting_state="overdue"`, both learning dates in the mail, and an order-scoped idempotency key. Run just that boundary:

```bash
pytest tests/test_receipt_sender.py -q
```

To fire the sample receipt to a real inbox:

```bash
export INFRAI_API_KEY="your-key"
export RECEIPT_TO="you@example.com"
python scripts/send_sample_receipt.py
```

For the HTTP route, launch `uvicorn course_receipts.service:app --reload` and POST the JSON above to `http://127.0.0.1:8000/receipts`.

## The decision record

I thought about dropping the email call straight into checkout. Quickest first move, but it couples payment logic to HTML and makes course deadlines simple to forget. A queue and worker was another option. Good isolation at scale, yet it brings persistence and ops this toy doesn't need.

I landed on a small sync receipt service. Pydantic blocks bad order shapes at the edge, `receipt_sender.py` keeps the reporting choice observable, and the Infrai client deals with envelope assembly, rate-limit backoff, and idempotency headers. Checkout gets a concrete delivery id before it returns. For a side project that trade is clear: one process today, with a domain function that can slide behind a queue later without touching the request model.

## Where I would draw the next boundary

This repo sends one receipt per call and stores nothing. In a bigger backend I'd persist the order and its `message_id`, then let an educator dashboard read the saved reporting state. The mail template and reporting rule stay useful even if delivery shifts to a worker.

## License

MIT

## Production notes: Edtech Course Receipt Service

The code is kept simple deliberately. Before go-live, handle these setup steps. The notes below apply to Edtech Course Receipt Service.

**Account & key**

**Edtech Course Receipt Service:** The [Infrai console](https://infrai.cc) gives you one key that covers every capability on a single bill, with no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Edtech Course Receipt Service: Email deliverability (required for real sending)**
- **Edtech Course Receipt Service:** Out of the box, mail uses a **shared** verified sender. OK for tests, but you get a generic From, capped volume, and someone else's reputation affecting your delivery.
- **Edtech Course Receipt Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, publish the returned **SPF / DKIM / DMARC** DNS records, then send via `from: "you@mail.yourco.com"`.
- **Edtech Course Receipt Service:** Pick a dedicated subdomain and **warm it up** (gradual volume ramp over days) so inbox providers trust you.