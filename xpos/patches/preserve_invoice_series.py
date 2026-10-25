"""Keep an operator's default invoice series selectable after schema sync."""
import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
    for doctype in ("Sales Invoice", "POS Invoice"):
        field = frappe.get_meta(doctype).get_field("naming_series")
        if not field or not field.default:
            continue
        options = (field.options or "").splitlines()
        if field.default not in options:
            make_property_setter(doctype, "naming_series", "options",
                                 "\n".join([*options, field.default]), "Text")
            frappe.clear_cache(doctype=doctype)
