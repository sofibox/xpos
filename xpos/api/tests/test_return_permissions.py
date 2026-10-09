import unittest
from unittest.mock import patch
import frappe
from xpos.x_pos.api.invoice import validate_return_access

class TestReturnPermissions(unittest.TestCase):
    def doc(self, is_return=1, qty=-1, profile='Counter'):
        return frappe._dict(pos_profile=profile, is_return=is_return, items=[frappe._dict(qty=qty)])

    def check(self, doc, role=True, enabled=True):
        with patch('xpos.api.auth.user_has_pos_permission', return_value=role) as right, patch('frappe.get_cached_doc', return_value=frappe._dict(allow_return=enabled)):
            validate_return_access(doc)
            return right

    def test_regular_sale_unchanged(self):
        self.assertFalse(self.check(self.doc(is_return=0, qty=1), role=False, enabled=False).called)

    def test_non_pos_invoice_unchanged(self):
        self.assertFalse(self.check(self.doc(profile=None), role=False, enabled=False).called)

    def test_cashier_denied_with_enabled_profile(self):
        with self.assertRaises(frappe.PermissionError): self.check(self.doc(), role=False)

    def test_cashier_denied_with_disabled_profile(self):
        with self.assertRaises(frappe.PermissionError): self.check(self.doc(), role=False, enabled=False)

    def test_manager_denied_with_disabled_profile(self):
        with self.assertRaises(frappe.PermissionError): self.check(self.doc(), enabled=False)

    def test_manager_allowed_with_enabled_profile(self):
        right=self.check(self.doc());right.assert_called_once_with('sale_return',pos_profile='Counter')

    def test_cashier_cannot_hide_return_flag(self):
        with self.assertRaises(frappe.PermissionError): self.check(self.doc(is_return=0), role=False)

    def test_manager_must_use_return_flag_for_negative_qty(self):
        with self.assertRaises(frappe.ValidationError): self.check(self.doc(is_return=0))
