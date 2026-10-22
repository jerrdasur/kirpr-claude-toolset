import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "kirpr" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import kirpr_fixture_transport as kft  # noqa: E402

BASE = kft.FIXTURE_BASE_URL
SAS = {"id": "SAS-200", "idReadable": "SAS-200", "summary": "Экспорт отчётов падает по таймауту",
       "description": "Экспорт больших отчётов обрывается через 30 с.",
       "reporter": {"login": "ivanov", "name": "Иван Иванов"}, "comments": [], "links": []}
PROJ = {"key": "PROJ-7", "fields": {"summary": "Jira-задача для фикстуры", "description": None,
                                    "reporter": {"displayName": "Пётр"}, "comment": {"comments": []},
                                    "issuelinks": [], "subtasks": []}}


def make_dir(root):
    d = Path(root) / "fixtures"
    d.mkdir()
    (d / "SAS-200.json").write_text(json.dumps(SAS, ensure_ascii=False), encoding="utf-8")
    (d / "PROJ-7.json").write_text(json.dumps(PROJ, ensure_ascii=False), encoding="utf-8")
    return d


class TestFixtureTransport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = make_dir(self.tmp.name)
        self.t = kft.fixture_transport(self.d)

    def test_youtrack_issue_with_query(self):
        status, raw = self.t("GET", f"{BASE}/api/issues/SAS-200?fields=idReadable,summary", {}, None)
        self.assertEqual((status, json.loads(raw)["idReadable"]), (200, "SAS-200"))

    def test_jira_singular_issue_path(self):
        status, raw = self.t("GET", f"{BASE}/rest/api/2/issue/PROJ-7?expand=changelog", {}, None)
        self.assertEqual((status, json.loads(raw)["key"]), (200, "PROJ-7"))

    def test_missing_issue_is_404_and_missing_sub_is_empty_list(self):
        self.assertEqual(self.t("GET", f"{BASE}/api/issues/SAS-999", {}, None)[0], 404)
        self.assertEqual(self.t("GET", f"{BASE}/api/issues/SAS-200/activities?x=1", {}, None), (200, b"[]"))
        self.assertEqual(self.t("GET", f"{BASE}/api/admin/projects", {}, None)[0], 404)

    def test_writes_are_logged_not_sent_and_gets_never_log(self):
        self.t("GET", f"{BASE}/api/issues/SAS-200", {}, None)
        self.assertFalse((self.d / "requests.log").exists())
        self.assertEqual(self.t("DELETE", f"{BASE}/api/issues/SAS-200", {}, None), (200, b"{}"))
        self.t("POST", f"{BASE}/api/issues/SAS-200/comments", {}, b'{"text":"x"}')
        self.assertEqual((self.d / "requests.log").read_text(encoding="utf-8").splitlines(),
                         ["DELETE /api/issues/SAS-200 ", 'POST /api/issues/SAS-200/comments {"text":"x"}'])


class TestFromEnv(unittest.TestCase):
    def test_absent_variable_returns_none(self):
        self.assertIsNone(kft.transport_from_env({}))

    def test_missing_directory_exits_without_network(self):
        with self.assertRaises(SystemExit) as cm:
            kft.transport_from_env({"EVAL_KIRPR_FIXTURES": "/nonexistent/dir"})
        self.assertIn("каталог не найден", str(cm.exception.code))


class TestScriptsInFixtureMode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = make_dir(self.tmp.name)

    def run_script(self, script, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("YOUTRACK_", "JIRA_"))}
        env["EVAL_KIRPR_FIXTURES"] = "fixtures"
        result = subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=self.tmp.name,
                                env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_fetch_youtrack_prints_issue(self):
        out = self.run_script("fetch_youtrack.py", "SAS-200")
        self.assertIn("# Экспорт отчётов падает по таймауту", out)
        self.assertIn("https://fixtures.invalid/issue/SAS-200", out)

    def test_fetch_jira_prints_issue(self):
        out = self.run_script("fetch_jira.py", "PROJ-7")
        self.assertIn("Jira-задача для фикстуры", out)

    def test_manage_youtrack_delete_preview_and_confirm(self):
        out = self.run_script("manage_youtrack.py", "--dry-run", "delete", "SAS-200")
        self.assertIn("Dry-run: удаление SAS-200", out)
        self.assertFalse((self.d / "requests.log").exists())
        self.run_script("manage_youtrack.py", "delete", "SAS-200", "--confirm", "SAS-200")
        self.assertIn("DELETE /api/issues/SAS-200", (self.d / "requests.log").read_text(encoding="utf-8"))


class TestRelativeDirFromSubdirectory(unittest.TestCase):
    def test_relative_dir_is_found_from_a_subdirectory(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_dir(tmp)
            sub = Path(tmp, "exportsrv", "pkg")
            sub.mkdir(parents=True)
            old = os.getcwd()
            os.chdir(sub)
            try:
                t = kft.transport_from_env({"EVAL_KIRPR_FIXTURES": "fixtures"})
            finally:
                os.chdir(old)
            self.assertEqual(t("GET", f"{BASE}/api/issues/SAS-200", {}, None)[0], 200)


if __name__ == "__main__":
    unittest.main()
