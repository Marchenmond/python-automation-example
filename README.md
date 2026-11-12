# Order Report Automation Example (Python)

**Result: a weekly CSV of orders becomes a finished report plus ready-to-send reminder e-mails in one command (9 tests passing).**

| | Before (by hand) | After (one command) |
|---|---|---|
| Weekly summary | Spreadsheet formulas, ~1 hour | `report.md` in under a second |
| Late payments | Easy to forget | One draft e-mail per late order |
| Bad data | Silent mistakes | Skipped rows listed with the reason |

A small command-line tool for a shop owner who exports orders to a CSV file every week and is tired of building the summary by hand. One command produces:

- `report.md` - revenue, average order, orders by status, revenue by month, top products and top customers;
- `email_drafts/<order_id>.txt` - a polite, ready-to-send reminder for every order that has been **pending** for too long;
- a list of **skipped rows** (bad e-mail, non-numeric quantity, etc.) so nothing fails silently.

All data in the examples is fictional. Python 3.9+, standard library only, no install step.

## Usage

```bash
python order_report.py examples/orders.csv --out examples/output --today 2025-03-31 --late-days 7
# 8 orders, 2 skipped, 1 e-mail drafts -> examples/output
```

CSV columns (header required): `order_id, date (YYYY-MM-DD), customer, email, product, qty, unit_price, status`.
Revenue counts only `paid` and `shipped` orders; `pending` and `cancelled` are listed in the status line but not added to revenue.

## Example

Input: [`examples/orders.csv`](examples/orders.csv): 10 rows in the file, 8 valid orders, 2 skipped (deliberately broken rows: a bad e-mail and a quantity of "zero"). That is why the tool prints `8 orders, 2 skipped`.
Output: [`examples/output/report.md`](examples/output/report.md) and [`examples/output/email_drafts/1004.txt`](examples/output/email_drafts/1004.txt).

```
Revenue (paid + shipped): $242.40   Average order: $48.48
Top customers: 1. Ivy Chen $89.90  2. Maya Fletcher $86.00  3. Owen Park $66.50
Skipped: line 10 (invalid e-mail: 'not-an-email'), line 11 (invalid quantity: 'zero')
```

Draft e-mail generated for the pending order 1004:

```
To: lena.rossi@example.com
Subject: About your order 1004

Hi Lena,
Thanks for ordering 3 x Cedar Candle ($55.50) on 2025-02-20. We noticed the payment is still pending. ...
```

## Tests

```bash
python -m unittest discover -s tests -v     # Ran 9 tests ... OK
```

They cover parsing, skipped rows, missing columns, revenue rules, rankings, the "late pending" selection, e-mail text and the full command-line run.

## Easy to adapt

Typical customizations for a client: different column names or date formats, Excel (.xlsx) input, sending drafts to Gmail/Outlook as real drafts, a weekly schedule (Task Scheduler / cron), PDF invoice organizing, or a Google Sheets export.

---
Built by Gabriel Montemór · Marchenmond — available on Upwork for small fixes and automations
