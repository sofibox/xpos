"""Public cashier names; never fall back to legal names or login identifiers."""
from copy import deepcopy
import frappe


def nickname(user):
    if not user or user == "Guest":
        return "STAFF"
    if not frappe.get_meta("User").has_field("custom_nickname"):
        return "STAFF"
    return str(frappe.db.get_value("User", user, "custom_nickname") or "").strip() or "STAFF"


def public_boot(boot):
    # Frappe may return cached boot data: do not alter Desk or another request.
    result = deepcopy(boot)
    for user, info in (result.get("user_info") or {}).items():
        if isinstance(info, dict):
            public_name = nickname(user)
            info["nickname"] = public_name
            for key in ("fullname", "full_name", "user_fullname"):
                if key in info:
                    info[key] = public_name
    user = result.get("user")
    if isinstance(user, dict):
        for key in ("fullname", "full_name", "user_fullname"):
            if key in user:
                user[key] = nickname(frappe.session.user)
    return result


@frappe.whitelist()
def get_my_nickname():
    return nickname(frappe.session.user)
