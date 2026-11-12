#!/usr/bin/env python3
"""Order report tool: turn a CSV export of orders into a summary report
and draft follow-up e-mails. Standard library only.

Usage:
    python order_report.py orders.csv --out output/ [--today 2025-03-31] [--late-days 7]
"""
import argparse
import csv
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

REQUIRED = ["order_id", "date", "customer", "email", "product", "qty", "unit_price", "status"]


def parse_orders(path):
    """Return (orders, problems). Bad rows are skipped and reported, never fatal."""
    orders, problems = [], []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("Missing column(s): " + ", ".join(missing))
        for line, row in enumerate(reader, start=2):
            try:
                try:
                    qty = int(row["qty"])
                except (ValueError, TypeError):
                    raise ValueError(f"invalid quantity: {row['qty']!r}")
                try:
                    price = float(row["unit_price"])
                except (ValueError, TypeError):
                    raise ValueError(f"invalid unit price: {row['unit_price']!r}")
                if qty <= 0 or price < 0:
                    raise ValueError("quantity must be above 0 and price cannot be negative")
                if "@" not in (row["email"] or ""):
                    raise ValueError(f"invalid e-mail: {row['email']!r}")
                try:
                    when = datetime.strptime(row["date"].strip(), "%Y-%m-%d").date()
                except (ValueError, AttributeError):
                    raise ValueError(f"invalid date: {row['date']!r} (use YYYY-MM-DD)")
                orders.append({
                    "order_id": row["order_id"].strip(),
                    "date": when,
                    "customer": row["customer"].strip(),
                    "email": row["email"].strip().lower(),
                    "product": row["product"].strip(),
                    "qty": qty,
                    "total": round(qty * price, 2),
                    "status": row["status"].strip().lower(),
                })
            except (ValueError, KeyError, AttributeError) as err:
                problems.append(f"line {line}: {err}")
    return orders, problems


def summarize(orders):
    """Revenue counts only paid and shipped orders; cancelled/pending are tracked apart."""
    counted = [o for o in orders if o["status"] in ("paid", "shipped")]
    by_product, by_customer, by_month = defaultdict(float), defaultdict(float), defaultdict(float)
    for o in counted:
        by_product[o["product"]] += o["total"]
        by_customer[o["customer"]] += o["total"]
        by_month[o["date"].strftime("%Y-%m")] += o["total"]
    statuses = defaultdict(int)
    for o in orders:
        statuses[o["status"]] += 1
    revenue = round(sum(o["total"] for o in counted), 2)
    return {
        "orders": len(orders),
        "revenue": revenue,
        "average_order": round(revenue / len(counted), 2) if counted else 0.0,
        "statuses": dict(sorted(statuses.items())),
        "top_products": sorted(((k, round(v, 2)) for k, v in by_product.items()), key=lambda x: -x[1])[:5],
        "top_customers": sorted(((k, round(v, 2)) for k, v in by_customer.items()), key=lambda x: -x[1])[:5],
        "by_month": sorted((k, round(v, 2)) for k, v in by_month.items()),
    }


def late_pending(orders, today, late_days):
    return [o for o in orders if o["status"] == "pending" and (today - o["date"]).days >= late_days]


def render_report(summary, problems, today):
    lines = [f"# Order report ({today.isoformat()})", "",
             f"- Orders read: **{summary['orders']}**",
             f"- Revenue (paid + shipped): **${summary['revenue']:,.2f}**",
             f"- Average order: **${summary['average_order']:,.2f}**",
             "- Status: " + ", ".join(f"{k} {v}" for k, v in summary["statuses"].items()), "",
             "## Revenue by month"]
    lines += [f"- {m}: ${v:,.2f}" for m, v in summary["by_month"]] or ["- none"]
    lines += ["", "## Top products"]
    lines += [f"{i}. {n} - ${v:,.2f}" for i, (n, v) in enumerate(summary["top_products"], 1)] or ["- none"]
    lines += ["", "## Top customers"]
    lines += [f"{i}. {n} - ${v:,.2f}" for i, (n, v) in enumerate(summary["top_customers"], 1)] or ["- none"]
    if problems:
        lines += ["", "## Rows skipped"] + [f"- {p}" for p in problems]
    return "\n".join(lines) + "\n"


def draft_email(order, shop_name="Maple & Pine Goods"):
    first = order["customer"].split()[0]
    return (f"To: {order['email']}\n"
            f"Subject: About your order {order['order_id']}\n\n"
            f"Hi {first},\n\n"
            f"Thanks for ordering {order['qty']} x {order['product']} (${order['total']:,.2f}) on "
            f"{order['date'].isoformat()}. We noticed the payment is still pending. "
            f"Could you check it on your side, or reply to this message if you need help?\n\n"
            f"Best regards,\n{shop_name}\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv_path")
    ap.add_argument("--out", default="output")
    ap.add_argument("--today", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(), default=date.today())
    ap.add_argument("--late-days", type=int, default=7)
    args = ap.parse_args(argv)
    try:
        orders, problems = parse_orders(args.csv_path)
    except (OSError, ValueError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(render_report(summarize(orders), problems, args.today), encoding="utf-8")
    late = late_pending(orders, args.today, args.late_days)
    drafts = out / "email_drafts"
    drafts.mkdir(exist_ok=True)
    for old in drafts.glob("*.txt"):
        old.unlink()
    for o in late:
        (drafts / f"{o['order_id']}.txt").write_text(draft_email(o), encoding="utf-8")
    print(f"{len(orders)} orders, {len(problems)} skipped, {len(late)} e-mail drafts -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
