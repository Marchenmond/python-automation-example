import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import order_report as r  # noqa: E402

SAMPLE = ROOT / "examples" / "orders.csv"


class ParseTests(unittest.TestCase):
    def test_sample_parses_and_skips_bad_rows(self):
        orders, problems = r.parse_orders(SAMPLE)
        self.assertEqual(len(orders), 8)
        self.assertEqual(len(problems), 2)
        self.assertTrue(any("line 10" in p and "e-mail" in p for p in problems))
        self.assertTrue(any("line 11" in p and "invalid quantity: 'zero'" in p for p in problems))

    def test_missing_column_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.csv"
            p.write_text("order_id,date\n1,2025-01-01\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                r.parse_orders(p)


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.orders, _ = r.parse_orders(SAMPLE)
        self.s = r.summarize(self.orders)

    def test_revenue_counts_only_paid_and_shipped(self):
        # 37.00 + 42.00 + 49.00 + 24.50 + 89.90
        self.assertEqual(self.s["revenue"], 242.40)
        self.assertEqual(self.s["average_order"], 48.48)

    def test_statuses_and_rankings(self):
        self.assertEqual(self.s["statuses"], {"cancelled": 1, "paid": 3, "pending": 2, "shipped": 2})
        self.assertEqual(self.s["top_products"][0], ("Wool Throw", 89.9))
        self.assertEqual(self.s["top_customers"][0], ("Ivy Chen", 89.9))
        self.assertEqual(self.s["by_month"], [("2025-02", 128.0), ("2025-03", 114.4)])

    def test_empty_input(self):
        s = r.summarize([])
        self.assertEqual((s["revenue"], s["average_order"]), (0.0, 0.0))


class DraftTests(unittest.TestCase):
    def test_late_pending_selection(self):
        orders, _ = r.parse_orders(SAMPLE)
        late = r.late_pending(orders, date(2025, 3, 31), 7)
        self.assertEqual([o["order_id"] for o in late], ["1004"])
        late3 = r.late_pending(orders, date(2025, 3, 31), 3)
        self.assertEqual([o["order_id"] for o in late3], ["1004", "1008"])

    def test_draft_content(self):
        orders, _ = r.parse_orders(SAMPLE)
        text = r.draft_email(orders[3])
        self.assertIn("To: lena.rossi@example.com", text)
        self.assertIn("Hi Lena,", text)
        self.assertIn("3 x Cedar Candle ($55.50)", text)


class CliTests(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            code = r.main([str(SAMPLE), "--out", d, "--today", "2025-03-31"])
            self.assertEqual(code, 0)
            report = (Path(d) / "report.md").read_text(encoding="utf-8")
            self.assertIn("$242.40", report)
            self.assertIn("Rows skipped", report)
            self.assertTrue((Path(d) / "email_drafts" / "1004.txt").exists())
            self.assertFalse((Path(d) / "email_drafts" / "1008.txt").exists())

    def test_missing_file_returns_error(self):
        self.assertEqual(r.main(["does-not-exist.csv", "--out", tempfile.gettempdir()]), 1)


if __name__ == "__main__":
    unittest.main()
