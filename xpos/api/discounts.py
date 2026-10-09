"""Validate untrusted POS discounts against role permissions and server pricing."""
import math
import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate


def validate_discount_payload(data, profile):
    from xpos.api.auth import user_has_pos_permission

    if not user_has_pos_permission('apply_additional_discount', pos_profile=profile.name):
        if flt(data.get('additional_discount_percentage')) or flt(data.get('discount_amount')):
            frappe.throw(_('You are not allowed to apply an additional discount.'), frappe.PermissionError)

    if user_has_pos_permission('show_edit_discount_field', pos_profile=profile.name):
        return

    from erpnext.stock.get_item_details import get_item_details

    for item in data.get('items', []):
        percentage = flt(item.get('discount_percentage'))
        amount = flt(item.get('discount_amount'))
        if cint(item.get('is_free_item')):
            frappe.throw(_('Free items require a user permitted to edit discounts.'), frappe.PermissionError)
        if not percentage and not amount:
            continue
        if not math.isfinite(percentage) or not math.isfinite(amount) or percentage < 0 or percentage > 100 or amount < 0:
            frappe.throw(_('Invalid item discount.'), frappe.PermissionError)
        # No client-supplied pricing-rule IDs, rates, warehouse, currency or price list
        # are trusted as proof that a promotion authorizes the requested discount.
        details = get_item_details(frappe._dict(
            doctype='Sales Invoice', company=profile.company,
            customer=data.get('customer'), item_code=item.get('item_code'),
            qty=flt(item.get('qty', 1)), uom=item.get('uom') or item.get('stock_uom'),
            warehouse=profile.warehouse, currency=profile.currency,
            selling_price_list=profile.selling_price_list, price_list=profile.selling_price_list,
            conversion_rate=1, plc_conversion_rate=1, is_pos=1,
            transaction_date=nowdate(), posting_date=nowdate(),
            ignore_pricing_rule=cint(profile.get('ignore_pricing_rule')),
        ))
        rules = details.get('pricing_rules')
        if isinstance(rules, str):
            rules = frappe.parse_json(rules)
        price = flt(details.get('price_list_rate'))
        requested = price * (1 - percentage / 100) if percentage else price - amount
        server_percentage = flt(details.get('discount_percentage'))
        server_amount = flt(details.get('discount_amount'))
        expected = price * (1 - server_percentage / 100) if server_percentage else price - server_amount
        if percentage and amount and abs(flt(requested, 6) - flt(price - amount, 6)) > 0.000001:
            frappe.throw(_('Inconsistent item discount.'), frappe.PermissionError)
        if not rules or price <= 0 or abs(flt(requested, 6) - flt(expected, 6)) > 0.000001:
            frappe.throw(_('Item discount is not authorized by an active pricing rule.'), frappe.PermissionError)
