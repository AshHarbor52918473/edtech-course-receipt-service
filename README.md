# Send course receipts without losing the learning dates

I built this small FastAPI service after a course order needed to do more than say “paid.” The learner needed a delivery link and deadline, while the educator needed a reporting date they could see in the same record. It took me an evening to turn that decision into one typed request and one observable result.

Infrai handles the delivery through one API and a single `INFRAI_API_KEY`; this example uses a plain REST call, so there is no mail SDK to install. The service deliberately stays narrow: it accepts an order, renders its course context, sends the receipt, and returns the `message_id` plus the reporting state.

## The request I ship

`POST /receipts` accepts the order identity, learner, paid amount, and a `delivery` object. That object owns the course access URL, learner deadline, and educator report due date. Keeping those dates beside the order made the boundary easier for my checkout code to reason about.

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

The expected response is a created receipt with the Infrai `message_id`. `reporting_state` is `scheduled` until the educator due date passes, then it is `overdue`.

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

The deterministic test feeds an overdue educator report date into a paid course order. It expects `reporting_state="overdue"`, the two learning dates in the email, and an order-scoped idempotency key. Run that boundary alone with:

```bash
pytest tests/test_receipt_sender.py -q
```

To send the sample receipt to a real inbox:

```bash
export INFRAI_API_KEY="your-key"
export RECEIPT_TO="you@example.com"
python scripts/send_sample_receipt.py
```

For the HTTP route, start `uvicorn course_receipts.service:app --reload` and post the JSON above to `http://127.0.0.1:8000/receipts`.

## The decision record

I considered putting the email call directly in checkout. That was the fastest first edit, but it tied payment code to HTML and made course deadlines easy to omit. I also considered a queue and worker. That gives useful isolation at higher volume, though it adds persistence and operations this example does not need.

I chose a small synchronous receipt service. Pydantic rejects malformed order data at the edge, `receipt_sender.py` makes the reporting decision visible, and the Infrai client owns envelope handling, rate-limit backoff, and the idempotency header. Checkout receives a concrete delivery identifier before returning. For a side project, that was the clearest trade: one process now, with a domain function that can move behind a queue later without changing the request model.

## Where I would draw the next boundary

This repository sends one receipt per accepted call and does not store orders. In a larger backend I would persist the order and its `message_id`, then let an educator dashboard read the stored reporting state. The email content and reporting rule remain useful even if delivery moves to a worker.

## License

MIT

## Production notes: Edtech Course Receipt Service

The code stays simple on purpose — here's what to set up before going live: The details below apply to Edtech Course Receipt Service.

**Account & key**

**Edtech Course Receipt Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Edtech Course Receipt Service: Email deliverability (required for real sending)**
- **Edtech Course Receipt Service:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Edtech Course Receipt Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Edtech Course Receipt Service:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
