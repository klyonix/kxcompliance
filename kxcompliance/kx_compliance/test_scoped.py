# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import ast
from pathlib import Path
from unittest import SkipTest
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from kxcompliance import scoped
from kxcompliance.kx_compliance.test_utils import TEST_COMPANY, make_company

APP = Path(__file__).resolve().parents[1]
# Patches and install run for the whole site; scoped.py is where the reads are allowed.
EXEMPT = {APP / "scoped.py", APP / "install.py"}
DIRECT_READS = {
	("frappe", "get_all"),
	("db", "get_value"),
	("db", "exists"),
	("db", "count"),
	("frappe", "get_cached_value"),
	("qb", "get_query"),
}
SETTINGS_READS = {"get_doc", "get_cached_doc", "get_single", "get_single_value"}
HOOKS = (
	"kxcompliance_scope",
	"kxcompliance_settings",
	"kxcompliance_check_limit",
	"kxcompliance_run_job",
	"kxcompliance_boot",
)
QUERY_TABLE_METHODS = {"from_", "update", "join", "left_join", "inner_join", "right_join"}


def app_sources():
	for path in sorted(APP.rglob("*.py")):
		if path in EXEMPT or path.name.startswith("test_") or path.name == "test_utils.py":
			continue
		if "patches" in path.relative_to(APP).parts:
			continue
		yield path, ast.parse(path.read_text())


def call_name(node: ast.Call) -> tuple[str | None, str] | None:
	if not isinstance(node.func, ast.Attribute):
		return None
	owner = node.func.value
	base = owner.attr if isinstance(owner, ast.Attribute) else getattr(owner, "id", None)
	return base, node.func.attr


def names_settings(node: ast.AST) -> bool:
	if isinstance(node, ast.Constant):
		return node.value == scoped.SETTINGS
	return isinstance(node, ast.Name) and node.id == "SETTINGS"


def unscoped_tables(function: ast.AST) -> list[str]:
	"""Query-builder tables a function queries without scoped.where on them."""
	tables, queried, scoped_names = set(), set(), set()
	for node in ast.walk(function):
		if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
			if call_name(node.value) == ("qb", "DocType"):
				tables.update(target.id for target in node.targets if isinstance(target, ast.Name))
		if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Name):
			name = call_name(node)
			if name == ("scoped", "where"):
				scoped_names.add(node.args[0].id)
			elif name and name[1] in QUERY_TABLE_METHODS:
				queried.add(node.args[0].id)
	return sorted((tables & queried) - scoped_names)


class TestEveryReadIsScoped(UnitTestCase):
	"""Another app narrows this app's own reads through `scoped`; a read that skips it would see
	every row whatever that app says."""

	def test_no_direct_reads(self):
		found = []
		for path, tree in app_sources():
			for node in ast.walk(tree):
				if isinstance(node, ast.Call) and call_name(node) in DIRECT_READS:
					base, method = call_name(node)
					found.append(f"{path.relative_to(APP)}:{node.lineno} {base}.{method}")
		self.assertEqual(found, [], "Read through kxcompliance.scoped instead")

	def test_settings_come_from_scoped(self):
		found = []
		for path, tree in app_sources():
			for node in ast.walk(tree):
				if not (isinstance(node, ast.Call) and node.args and names_settings(node.args[0])):
					continue
				name = call_name(node)
				if name and name[1] in SETTINGS_READS:
					found.append(f"{path.relative_to(APP)}:{node.lineno}")
		self.assertEqual(found, [], "Use scoped.settings() (for_update=True to save)")

	def test_every_queried_table_is_scoped(self):
		found = []
		for path, tree in app_sources():
			for node in ast.walk(tree):
				if isinstance(node, ast.FunctionDef):
					for table in unscoped_tables(node):
						found.append(f"{path.relative_to(APP)}:{node.lineno} {node.name}: {table}")
		self.assertEqual(found, [], "Add .where(scoped.where(table)) for each table")


class TestMerge(UnitTestCase):
	def test_merge_keeps_the_given_filters_and_adds_the_extra(self):
		extra = {"owner": "a@example.com"}
		self.assertEqual(scoped.merge(None, extra), extra)
		self.assertEqual(scoped.merge("X-1", extra), {"name": "X-1", **extra})
		self.assertEqual(scoped.merge({"status": "Open"}, extra), {"status": "Open", **extra})
		self.assertEqual(
			scoped.merge([["status", "=", "Open"]], extra),
			[["status", "=", "Open"], ["owner", "=", "a@example.com"]],
		)
		self.assertEqual(
			scoped.merge(["status", "=", "Open"], {"owner": ("in", ["a", "b"])}),
			[["status", "=", "Open"], ["owner", "in", ["a", "b"]]],
		)

	def test_both_apply_when_they_name_the_same_field(self):
		self.assertEqual(
			scoped.merge("x@example.com", {"name": ("in", ["x@example.com", "y@example.com"])}),
			[["name", "=", "x@example.com"], ["name", "in", ["x@example.com", "y@example.com"]]],
		)
		self.assertEqual(
			scoped.merge({"owner": ("!=", "b"), "status": "Open"}, {"owner": "a"}),
			[["owner", "!=", "b"], ["status", "=", "Open"], ["owner", "=", "a"]],
		)


def only_mine(doctype: str):
	return {"owner": "only-me@example.com"} if doctype == "Company" else None


class TestScopedReads(IntegrationTestCase):
	"""How `scoped` behaves on its own: run on a site where no app uses its hooks."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if any(frappe.get_hooks(hook) for hook in HOOKS):
			raise SkipTest("another app on this site uses the kxcompliance hooks")
		make_company()

	def hooked(self, name: str, path: str):
		real = frappe.get_hooks

		def get_hooks(hook=None, *args, **kwargs):
			if hook == name:
				return [path]
			return real(hook, *args, **kwargs)

		return patch("frappe.get_hooks", side_effect=get_hooks)

	def test_without_a_hook_reads_are_unchanged(self):
		self.assertEqual(scoped.conditions("Company"), {})
		self.assertTrue(scoped.exists("Company", TEST_COMPANY))
		self.assertEqual(
			scoped.get_all("Company", filters={"name": TEST_COMPANY}, pluck="name"), [TEST_COMPANY]
		)
		company = frappe.qb.DocType("Company")
		query = frappe.qb.from_(company).select(company.name).where(scoped.where(company))
		self.assertNotIn("WHERE", query.get_sql())

	def test_a_hook_narrows_every_kind_of_read(self):
		with self.hooked("kxcompliance_scope", f"{__name__}.only_mine"):
			self.assertFalse(scoped.exists("Company", TEST_COMPANY))
			self.assertIsNone(scoped.get_value("Company", TEST_COMPANY, "company_name"))
			self.assertIsNone(scoped.get_cached_value("Company", TEST_COMPANY, "company_name"))
			self.assertEqual(scoped.count("Company", {"name": TEST_COMPANY}), 0)
			self.assertEqual(scoped.get_all("Company", filters={"name": TEST_COMPANY}), [])
			company = frappe.qb.DocType("Company")
			rows = (
				frappe.qb.from_(company)
				.select(company.name)
				.where(company.name == TEST_COMPANY)
				.where(scoped.where(company))
			).run()
			self.assertEqual(rows, ())
			# Other doctypes are left alone.
			self.assertTrue(scoped.exists("User", "Administrator"))

	def test_settings_come_from_the_hook_when_it_gives_them(self):
		stand_in = frappe._dict(app_name="Stand-in")
		with patch(f"{__name__}.settings_hook", return_value=stand_in) as hook:
			with self.hooked("kxcompliance_settings", f"{__name__}.settings_hook"):
				self.assertEqual(scoped.settings().app_name, "Stand-in")
				stand_in.update(doctype="Other Settings", name="OS-1")
				self.assertEqual(scoped.settings_record(), {"doctype": "Other Settings", "name": "OS-1"})
				scoped.settings(for_update=True)
			hook.assert_called_with(for_update=True)
		self.assertEqual(scoped.settings().doctype, scoped.SETTINGS)
		self.assertEqual(scoped.settings_record(), {"doctype": scoped.SETTINGS, "name": scoped.SETTINGS})

	def test_a_limit_hook_can_refuse(self):
		with patch(f"{__name__}.limit_hook", side_effect=frappe.ValidationError("over")) as hook:
			with self.hooked("kxcompliance_check_limit", f"{__name__}.limit_hook"):
				self.assertRaises(frappe.ValidationError, scoped.check_limit, "Company", name="X")
			hook.assert_called_once_with("Company", name="X")

	def test_other_apps_add_notices_and_account_links(self):
		self.assertEqual(scoped.boot_extras(), {"notices": [], "account_links": []})
		given = {"notices": [{"text": "Trial ends soon"}], "account_links": [{"label": "Plan", "url": "/p"}]}
		with patch(f"{__name__}.boot_hook", return_value=given):
			with self.hooked("kxcompliance_boot", f"{__name__}.boot_hook"):
				self.assertEqual(scoped.boot_extras(), given)

	def test_a_job_hook_takes_the_job_or_lets_it_run(self):
		ran = []

		def job():
			ran.append(1)

		scoped.run_job(job)
		self.assertEqual(ran, [1])
		with patch(f"{__name__}.job_hook", return_value=True) as hook:
			with self.hooked("kxcompliance_run_job", f"{__name__}.job_hook"):
				scoped.run_job(job)
			hook.assert_called_once_with(job)
		self.assertEqual(ran, [1])


def settings_hook(for_update: bool = False):
	return None


def limit_hook(kind: str, **context):
	return None


def job_hook(job):
	return False


def boot_hook():
	return None
