"""Regression coverage for purchasing data exposed to sales-only users."""
import inspect
import unittest
from unittest.mock import MagicMock, patch

import frappe
from xpos.x_pos.api import purchase_orders, stock_transfer


class TestPurchaseAccess(unittest.TestCase):
	def test_every_purchase_endpoint_denies_before_body(self):
		endpoints = [f for _, f in inspect.getmembers(purchase_orders, inspect.isfunction)
			if f in frappe.whitelisted and f.__module__ == purchase_orders.__name__]
		self.assertGreaterEqual(len(endpoints), 20)
		with patch.object(purchase_orders, "frappe") as api:
			api.has_permission.return_value = False
			api.PermissionError = PermissionError
			api.throw.side_effect = PermissionError
			for endpoint in endpoints:
				with self.subTest(endpoint=endpoint.__name__):
					# Missing arguments intentionally: permission must run before the body.
					with self.assertRaises(PermissionError):
						endpoint()
			api.get_all.assert_not_called()
			api.get_list.assert_not_called()
			api.get_doc.assert_not_called()
			api.db.sql.assert_not_called()

	def test_purchase_order_or_invoice_reader_can_enter(self):
		for permitted in ("Purchase Order", "Purchase Invoice"):
			with self.subTest(permitted=permitted), patch.object(purchase_orders, "frappe") as api:
				api.has_permission.side_effect = lambda dt, p: dt == permitted
				body = MagicMock(return_value="allowed")
				self.assertEqual(purchase_orders.require_purchase_access(body)("arg"), "allowed")
				body.assert_called_once_with("arg")

	def test_supplier_search_uses_permission_filtered_list(self):
		with patch.object(purchase_orders, "frappe") as api:
			api.has_permission.return_value = True
			api.get_list.return_value = [{"name": "visible"}]
			self.assertEqual(purchase_orders.search_suppliers(), [{"name": "visible"}])
			self.assertEqual(api.get_list.call_args.args[0], "Supplier")
			api.get_all.assert_not_called()


class TestTransferAccess(unittest.TestCase):
	def test_all_transfer_endpoints_deny_before_database_access(self):
		for function, args in ((stock_transfer.get_in_transit_transfers, ()),
			(stock_transfer.get_transfer_detail, ("hidden",)),
			(stock_transfer.receive_transit_stock, ({},)),
			(stock_transfer.return_shortage_to_source, ({},))):
			with self.subTest(endpoint=function.__name__), patch.object(stock_transfer, "frappe") as api:
				api.has_permission.side_effect = PermissionError
				with self.assertRaises(PermissionError):
					function(*args)
				api.get_doc.assert_not_called()
				api.get_all.assert_not_called()
				api.get_list.assert_not_called()
				api.db.exists.assert_not_called()

	def test_detail_checks_document_permission(self):
		with patch.object(stock_transfer, "frappe") as api:
			api.get_doc.return_value.check_permission.side_effect = PermissionError
			with self.assertRaises(PermissionError):
				stock_transfer.get_transfer_detail("other-company")
			api.get_doc.return_value.check_permission.assert_called_once_with("read")

	def test_transfer_list_uses_permission_filtered_query(self):
		with patch.object(stock_transfer, "frappe") as api:
			api.get_list.return_value = []
			self.assertEqual(stock_transfer.get_in_transit_transfers(), [])
			self.assertEqual(api.get_list.call_args.args[0], "Stock Entry")
			api.get_all.assert_not_called()

	def test_receive_requires_submit_as_well_as_create(self):
		with patch.object(stock_transfer, "frappe") as api:
			api.has_permission.side_effect = [True, PermissionError]
			with self.assertRaises(PermissionError):
				stock_transfer.receive_transit_stock({})
			self.assertEqual(api.has_permission.call_args.args, ("Stock Entry", "submit"))
			api.get_doc.assert_not_called()
