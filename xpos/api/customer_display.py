"""Server-backed Customer Display configuration.

The browser keeps a local copy for offline use, while this API stores the
authoritative configuration per terminal in the ERPNext site database.
"""

import json
import os
import re
from urllib.parse import urlsplit

import frappe
from frappe import _


DOCTYPE = "XPOS Customer Display"
MAX_TERMINAL_ID_LENGTH = 160
MAX_CONFIGURATION_BYTES = 512 * 1024
TERMINAL_ID_PATTERN = re.compile(r"^[^\x00-\x1f\x7f]{1,160}$")


def _require_authenticated_user() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Please sign in to use Customer Display settings."), frappe.PermissionError)


def _require_settings_manager() -> None:
	_require_authenticated_user()
	if frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles(frappe.session.user):
		return
	frappe.throw(
		_("Only a System Manager can change the shared Customer Display configuration."),
		frappe.PermissionError,
	)


def _validate_terminal_id(terminal_id: str) -> str:
	terminal_id = (terminal_id or "").strip()
	if not TERMINAL_ID_PATTERN.fullmatch(terminal_id):
		frappe.throw(_("Terminal ID must be between 1 and {0} printable characters.").format(MAX_TERMINAL_ID_LENGTH))
	return terminal_id


def _parse_configuration(configuration: str | dict) -> dict:
	if isinstance(configuration, str):
		if len(configuration.encode("utf-8")) > MAX_CONFIGURATION_BYTES:
			frappe.throw(_("Customer Display configuration is too large."))
		try:
			configuration = json.loads(configuration)
		except json.JSONDecodeError:
			frappe.throw(_("Customer Display configuration must be valid JSON."))
	if not isinstance(configuration, dict):
		frappe.throw(_("Customer Display configuration must be an object."))
	if set(configuration) - {"settings", "playlist"}:
		frappe.throw(_("Customer Display configuration contains unsupported fields."))
	if not isinstance(configuration.get("settings", {}), dict) or not isinstance(configuration.get("playlist", []), list):
		frappe.throw(_("Customer Display settings or playlist has an invalid format."))
	return configuration


@frappe.whitelist()
def get_configuration(terminal_id: str) -> dict:
	"""Return the saved configuration for one terminal, or an empty payload."""
	_require_authenticated_user()
	terminal_id = _validate_terminal_id(terminal_id)
	name = frappe.db.get_value(DOCTYPE, {"terminal_id": terminal_id}, "name")
	if not name:
		return {"configuration": None, "modified": None}
	doc = frappe.get_doc(DOCTYPE, name)
	try:
		configuration = json.loads(doc.configuration or "{}")
	except json.JSONDecodeError:
		frappe.log_error("Invalid saved Customer Display configuration", DOCTYPE)
		configuration = {}
	return {"configuration": configuration, "modified": doc.modified}


@frappe.whitelist()
def list_configurations() -> list[dict]:
	"""List saved display setups without exposing their configuration payload."""
	_require_authenticated_user()
	return frappe.get_all(
		DOCTYPE,
		fields=["terminal_id", "modified"],
		order_by="modified desc",
		limit_page_length=100,
	)


@frappe.whitelist()
def delete_configuration(terminal_id: str) -> None:
	"""Delete one saved display setup, without deleting uploaded Frappe Files."""
	_require_settings_manager()
	terminal_id = _validate_terminal_id(terminal_id)
	name = frappe.db.get_value(DOCTYPE, {"terminal_id": terminal_id}, "name")
	if not name:
		frappe.throw(_("Customer Display setup was not found."), frappe.DoesNotExistError)
	frappe.delete_doc(DOCTYPE, name)


@frappe.whitelist()
def check_assets(file_urls: str | list) -> list[dict]:
	"""Check whether uploaded Frappe Files referenced by a playlist still exist.

	External URLs are deliberately reported as external rather than fetched by
	the ERPNext server; their availability and CORS policy belong to their host.
	"""
	_require_authenticated_user()
	if isinstance(file_urls, str):
		try:
			file_urls = json.loads(file_urls)
		except json.JSONDecodeError:
			frappe.throw(_("Media URLs must be valid JSON."))
	if not isinstance(file_urls, list) or len(file_urls) > 100:
		frappe.throw(_("Choose up to 100 media files to check."))

	results = []
	for value in file_urls:
		if not isinstance(value, str) or not value:
			continue
		file_url = urlsplit(value).path
		if not file_url.startswith("/files/"):
			results.append({"url": value, "status": "external"})
			continue
		name = frappe.db.get_value("File", {"file_url": file_url}, "name")
		if not name:
			results.append({"url": value, "status": "missing"})
			continue
		file_doc = frappe.get_doc("File", name)
		results.append(
			{
				"url": value,
				"status": "available" if os.path.exists(file_doc.get_full_path()) else "missing",
			}
		)
	return results


@frappe.whitelist()
def save_configuration(terminal_id: str, configuration: str | dict) -> dict:
	"""Persist one terminal's settings and playlist.

	Only System Managers may change this shared configuration. Customer-facing
	transaction data is never part of this payload.
	"""
	_require_settings_manager()
	terminal_id = _validate_terminal_id(terminal_id)
	configuration = _parse_configuration(configuration)
	serialized = json.dumps(configuration, ensure_ascii=False, separators=(",", ":"))
	if len(serialized.encode("utf-8")) > MAX_CONFIGURATION_BYTES:
		frappe.throw(_("Customer Display configuration is too large."))
	name = frappe.db.get_value(DOCTYPE, {"terminal_id": terminal_id}, "name")
	if name:
		doc = frappe.get_doc(DOCTYPE, name)
		doc.configuration = serialized
		doc.save()
	else:
		doc = frappe.get_doc({"doctype": DOCTYPE, "terminal_id": terminal_id, "configuration": serialized})
		doc.insert()
	return {"modified": doc.modified}


@frappe.whitelist()
def create_configuration(terminal_id: str, configuration: str | dict) -> dict:
	"""Create a named display setup and reject duplicate names."""
	_require_settings_manager()
	terminal_id = _validate_terminal_id(terminal_id)
	if frappe.db.exists(DOCTYPE, {"terminal_id": terminal_id}):
		frappe.throw(_("A saved Customer Display setup already uses this name. Choose another name."))
	configuration = _parse_configuration(configuration)
	serialized = json.dumps(configuration, ensure_ascii=False, separators=(",", ":"))
	if len(serialized.encode("utf-8")) > MAX_CONFIGURATION_BYTES:
		frappe.throw(_("Customer Display configuration is too large."))
	doc = frappe.get_doc({"doctype": DOCTYPE, "terminal_id": terminal_id, "configuration": serialized})
	doc.insert()
	return {"modified": doc.modified}
