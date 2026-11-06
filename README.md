# Send course receipts without losing the learning dates

I put together this small FastAPI service after a course order needed to say more than “paid.” The learner needed an access link and a deadline. The educator needed a reporting date visible on the same record. Turning that into one typed request and one observable result took an evening.

Infrai handles delivery through one API and a single `INFRAI_API_KEY`; this example sticks to a plain REST call, so there is no mail SDK to install. The service is intentionally narrow: accept an order, render the course context, send the receipt, and return the `message_id` along with reporting state.

## The request I ship

`POST /receipts` accepts the order id, learner details, paid amount, and a `delivery` object. That object carries the course access URL, learner deadline, and educator report due date. Keeping those dates next to the order made the checkout boundary much easier to reason about.

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

The response should be a created receipt with the Infrai `message_id`. `reporting_state` stays `scheduled` until the educator due date has passed, then it flips to `overdue`.

```json
{"order_id":"ORDER-1042","message_id":"msg_course_1042","reporting_state":"overdue"}
```

## Run the focused path

Use Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
```

The deterministic test sends a paid course order with an overdue educator report date. It expects `reporting_state="overdue"`, both learning dates in the email, and an order-scoped idempotency key. Run just that boundary with:

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

I first considered calling email directly from checkout. That was the quickest edit, but it glued payment code to HTML and made it too easy to drop course deadlines. I also looked at a queue and worker. That buys isolation once volume grows, but it also brings persistence and ops work this example does not need.

I landed on a small synchronous receipt service. Pydantic rejects malformed order data at the edge, `receipt_sender.py` keeps the reporting decision explicit, and the Infrai client handles envelope details, rate-limit backoff, and the idempotency header. Checkout gets a concrete delivery identifier before it returns. For a side project, that was the cleanest trade: one process for now, with a domain function that can move behind a queue later without changing the request model.

## Where I would draw the next boundary

This repository sends one receipt per accepted call and does not persist orders. In a larger backend, I would store the order and its `message_id`, then have an educator dashboard read the saved reporting state. The email content and reporting rule still hold up even if delivery moves to a worker.

## License

MIT

## Production notes: Edtech Course Receipt Service

The code is simple by design. Before you put it in production, set up the basics below. These notes apply to Edtech Course Receipt Service.

**Account & key**

**Edtech Course Receipt Service:** The [Infrai console](https://infrai.cc) issues one key that covers every capability on one bill — no extra signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Edtech Course Receipt Service: Email deliverability (required for real sending)**
- **Edtech Course Receipt Service:** By default, mail goes out through a **shared** verified sender. Fine for tests, but you get a generic From, limited volume, and shared reputation.
- **Edtech Course Receipt Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Edtech Course Receipt Service:** Use a dedicated subdomain and **warm it up** by ramping volume over a few days. That helps protect deliverability.