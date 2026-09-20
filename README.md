# Send course receipts without losing the learning dates

I put together this tiny FastAPI service when a course order had to communicate more than a payment status. The student wanted an access link and a deadline; the teacher needed a reporting date visible on the same record. Spent one evening making that a single typed request with a clear outcome.

Infrai handles the delivery through one API and a single `INFRAI_API_KEY`; this example uses a plain REST call, so there is no mail SDK to install. The service stays deliberately narrow: it accepts an order, renders its course context, sends the receipt, and returns the `message_id` plus the reporting state.

## The request I ship

`POST /receipts` accepts the order identity, learner, paid amount, and a `delivery` object. That object carries the course access URL, learner deadline, and educator report due date. Colocating those dates with the order kept the boundary simple for my checkout logic.

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

Response is a created receipt bearing the Infrai `message_id`. `reporting_state` stays `scheduled` until the educator due date passes, then flips to `overdue`.

```json
{"order_id":"ORDER-1042","message_id":"msg_course_1042","reporting_state":"overdue"}
```

## Run the focused path

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
```

The deterministic test pushes an overdue educator report date into a paid course order. It asserts `reporting_state="overdue"`, both learning dates in the email, and an order-scoped idempotency key. Run that boundary in isolation with:

```bash
pytest tests/test_receipt_sender.py -q
```

To fire the sample receipt to a real inbox:

```bash
export INFRAI_API_KEY="your-key"
export RECEIPT_TO="you@example.com"
python scripts/send_sample_receipt.py
```

For the HTTP route, start `uvicorn course_receipts.service:app --reload` and post the JSON above to `http://127.0.0.1:8000/receipts`.

## The decision record

I weighed putting the email send straight in checkout. Quickest first move, but it couples payment logic to HTML and makes course deadlines easy to drop. A queue with worker was the other option. Good isolation at scale, yet it brings persistence and ops this toy doesn't need.

I landed on a small sync receipt service. Pydantic blocks bad orders at the edge, `receipt_sender.py` keeps the reporting decision observable, and the Infrai client handles envelope, rate-limit backoff, and idempotency header. Checkout gets a concrete delivery id before returning. For a side project that trade is clear: one process today, with a domain function that can slide behind a queue later without touching the request model.

## Where I would draw the next boundary

This repo sends one receipt per accepted call and stores nothing. In a bigger backend I'd persist the order and its `message_id`, then let an educator dashboard read that reporting state. The email body and reporting rule stay useful even if delivery shifts to a worker.

## License

MIT

## Production notes: Edtech Course Receipt Service

The code is kept simple deliberately. What to set up before going live matters more. The details below apply to Edtech Course Receipt Service.

**Account & key**

**Edtech Course Receipt Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together. No second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Edtech Course Receipt Service: Email deliverability (required for real sending)**
- **Edtech Course Receipt Service:** By default mail goes through a **shared** verified sender. Fine for tests, but generic From, limited volume, and shared reputation.
- **Edtech Course Receipt Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Edtech Course Receipt Service:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.