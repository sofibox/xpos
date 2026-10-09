"""The cart preview must honor the same Price List restriction as invoice pricing."""
import unittest
from unittest.mock import MagicMock, patch

from xpos.api.pricing_rules import apply_item_rules


class TestPricingPriceList(unittest.TestCase):
    def test_passes_selling_price_list_to_item_rule_engine(self):
        doc = MagicMock()
        doc.doctype = "Sales Invoice"
        doc.name = None
        doc.posting_date = "2026-10-09"
        doc.selling_price_list = "Retail - MYR"
        doc.meta.get_valid_columns.return_value = ["selling_price_list"]
        doc.get.side_effect = lambda field: getattr(doc, field, None)
        row = MagicMock()
        row.doctype = "Sales Invoice Item"
        row.name = None
        row.rate = 50
        row.qty = 1
        row.as_dict.return_value = {"item_code": "TEST", "qty": 1, "rate": 50}
        doc.items = [row]
        with patch("erpnext.accounts.doctype.pricing_rule.pricing_rule.get_pricing_rule_for_item", return_value={}) as engine, patch("erpnext.accounts.doctype.pricing_rule.pricing_rule.set_transaction_type"):
            apply_item_rules(doc)
        args = engine.call_args.args[0]
        self.assertEqual(args.price_list, "Retail - MYR")
        self.assertEqual(args.selling_price_list, "Retail - MYR")
        self.assertEqual(args.transaction_date, "2026-10-09")
