# Copyright (c) 2026, Ali Raza and contributors
# For license information, please see license.txt

import frappe
import base64
import mimetypes
from frappe import _
from frappe.utils import cint

REPRINT_DOCTYPES = ("Sales Invoice", "POS Invoice")


@frappe.whitelist()
def get_print_formats(doctype: str = "Sales Invoice"):
	"""Returns available print format names for a doctype."""
	print_formats = frappe.get_all(
		"Print Format",
		filters={"doc_type": doctype, "disabled": 0},
		fields=["name"],
	)
	return [p.name for p in print_formats]


def can_reprint(user: str | None = None) -> bool:
	"""Whether ``user`` may reprint a posted POS invoice (the ``allow_reprint_invoice`` right)."""
	from xpos.api.auth import user_has_pos_permission

	return user_has_pos_permission("allow_reprint_invoice", user)


def invoice_has_permission(doc, ptype: str, user: str) -> bool:
	"""``has_permission`` hook restricting reprinting of POS invoices."""
	if ptype != "print":
		return True
	if not getattr(doc, "is_pos", 0):
		return True
	if cint(getattr(doc, "print_count", 0)) < 1:
		return True
	return can_reprint(user)


@frappe.whitelist()
def get_receipt_context(pos_profile: str, print_format: str | None = None) -> dict:
	"""Resolve everything the desktop app needs to render a receipt offline."""
	profile = frappe.get_cached_doc("POS Profile", pos_profile)
	company = frappe.get_cached_doc("Company", profile.company)

	address = ""
	address_name = profile.get("company_address") or company.get("company_address")
	if address_name:
		addr = frappe.get_cached_doc("Address", address_name)
		address = "\n".join(
			p
			for p in [
				addr.address_line1,
				addr.address_line2,
				" ".join(filter(None, [addr.pincode, addr.city])) + (", " + addr.state if addr.state else ""),
			]
			if p
		)

	# Embed a local public logo so an actual disconnected print needs no network request.
	logo = profile.get("custom_receipt_logo") or company.get("company_logo") or ""
	if logo.startswith("/files/"):
		file_name = frappe.db.get_value("File", {"file_url": logo, "is_private": 0}, "name")
		if file_name:
			file_doc = frappe.get_doc("File", file_name)
			content = file_doc.get_content()
			mime = mimetypes.guess_type(logo)[0] or "image/png"
			if isinstance(content, bytes) and len(content) <= 1024 * 1024 and mime in ("image/png", "image/jpeg", "image/webp"):
				logo = "data:" + mime + ";base64," + base64.b64encode(content).decode("ascii")

	fmt = print_format or profile.get("print_format") or profile.get("default_print_format") or "XPOS Thermal Receipt"
	css = frappe.db.get_value("Print Format", fmt, "css") or ""

	return {
		"company_name": company.company_name or company.name,
		"company_phone": company.get("phone_no") or "",
		"company_email": profile.get("custom_receipt_email") or "",
		"company_website": company.get("website") or "",
		"company_address": address,
		"company_tax_id": "",  # Identity tax numbers are never needed by this receipt renderer.
		"company_registration_no": profile.get("custom_receipt_registration_no") or "",
		"receipt_message": profile.get("custom_receipt_message") or "",
		"receipt_brand": profile.get("custom_receipt_brand") or "LOZiPOS",
		"company_logo": logo,
		"receipt_header": company.get("receipt_header") or "",
		"receipt_footer": company.get("receipt_footer") or "",
		"currency": company.get("default_currency") or "",
		"print_discount_amount": cint(profile.get("print_discount_amount")),
		"print_format": fmt,
		"css": css,
	}


@frappe.whitelist()
def mark_invoice_printed(doctype: str, name: str) -> dict:
	"""Record that a POS receipt has printed, so later prints count as reprints."""
	if doctype not in REPRINT_DOCTYPES:
		frappe.throw(_("Unsupported doctype for print tracking: {0}").format(doctype))
	current = cint(frappe.db.get_value(doctype, name, "print_count"))
	frappe.db.set_value(doctype, name, "print_count", current + 1, update_modified=False)
	return {"name": name, "print_count": current + 1}
