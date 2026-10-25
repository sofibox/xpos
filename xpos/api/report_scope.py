"""Server-side scope for cashier stock and shift reports, including direct Desk calls."""
import frappe
from frappe import _
from xpos.api.auth import is_superuser, user_has_pos_permission


def _profiles():
    names = frappe.get_all("POS Profile User", filters={"parenttype": "POS Profile", "user": frappe.session.user}, pluck="parent")
    if not names:
        frappe.throw(_("No POS Profile is assigned to your account."), frappe.PermissionError)
    return [frappe.get_cached_doc("POS Profile", name) for name in set(names)]


def stock_scope(filters):
    if is_superuser(frappe.session.user) or "Stock Manager" in frappe.get_roles():
        return filters
    profiles = _profiles()
    company = filters.get("company")
    if not company or company not in {p.company for p in profiles}:
        frappe.throw(_("Choose a company assigned to your POS Profile."), frappe.PermissionError)
    assigned = {p.warehouse for p in profiles if p.company == company and p.warehouse}
    visible = set(frappe.get_list("Warehouse", filters={"name": ["in", list(assigned)], "company": company}, pluck="name", limit_page_length=0))
    requested = filters.get("warehouse") or []
    if isinstance(requested, str): requested = [w.strip() for w in requested.split(",") if w.strip()]
    if not visible or not set(requested).issubset(visible):
        frappe.throw(_("This warehouse is not assigned to your POS Profile."), frappe.PermissionError)
    filters["warehouse"] = list(requested or sorted(visible))
    return filters


def shift_scope(filters):
    if is_superuser(frappe.session.user):
        return filters
    profiles = {p.name: p for p in _profiles()}
    name = filters.get("pos_opening_shift")
    if not name:
        frappe.throw(_("Select your opening shift to view its reconciliation."))
    shift = frappe.get_doc("POS Opening Shift", name)
    shift.check_permission("read")
    if shift.pos_profile not in profiles or not user_has_pos_permission("shift_report", pos_profile=shift.pos_profile):
        frappe.throw(_("You do not have access to this shift report."), frappe.PermissionError)
    if shift.owner != frappe.session.user and not user_has_pos_permission("recall_other_shift_tabs", pos_profile=shift.pos_profile):
        frappe.throw(_("You can only view your own shift report."), frappe.PermissionError)
    filters["company"] = shift.company
    filters["pos_profile"] = shift.pos_profile
    return filters
