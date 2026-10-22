import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kirpr", "scripts"))
import kirpr_memory as km  # noqa: E402

GOOD = """# Память: scansrv

## Как проверять
- `make test`

## Ловушки
- `*_zenrpc.go` генерируется `make generate`

## Уроки
- [L-003] шаг ссылался на `Jobs().Summary`, в коде `Jobs().Info` → сверять сигнатуры с кодом (SAS-200; 2026-10-22; refs: pkg/rpc/scan.go, pkg/rpc/job.go)
- [L-004] задача без негативного сценария → добавлять «Проверить» с ошибкой (SAS-201; 2026-10-23)
"""


class TestParse(unittest.TestCase):
    def test_parses_lessons_with_and_without_refs(self):
        mem = km.parse_memory(GOOD)
        self.assertEqual(mem.title, "Память: scansrv")
        self.assertEqual([l.number for l in mem.lessons], [3, 4])
        self.assertEqual(mem.lessons[0].refs, ["pkg/rpc/scan.go", "pkg/rpc/job.go"])
        self.assertEqual(mem.lessons[0].task, "SAS-200")
        self.assertEqual(mem.lessons[1].refs, [])
        self.assertIn("→", mem.lessons[0].text)

    def test_format_roundtrip(self):
        mem = km.parse_memory(GOOD)
        self.assertEqual(km.format_lesson(mem.lessons[0]), GOOD.splitlines()[9])


class TestLint(unittest.TestCase):
    def test_good_file_has_no_errors(self):
        self.assertEqual(km.lint_memory(GOOD), [])

    def test_missing_section_and_wrong_order(self):
        errors = km.lint_memory(GOOD.replace("## Ловушки\n", ""))
        self.assertTrue(any("## Ловушки" in e for e in errors))
        swapped = (GOOD.replace("## Как проверять", "## X")
                   .replace("## Ловушки", "## Как проверять")
                   .replace("## X", "## Ловушки"))
        self.assertTrue(any("порядок" in e for e in km.lint_memory(swapped)))

    def test_bad_lesson_line_and_duplicate_id(self):
        errors = km.lint_memory(GOOD + "- [L-004] без стрелки и метаданных\n")
        self.assertTrue(any("L-004" in e and "дубл" in e for e in errors))
        self.assertTrue(any("формат" in e for e in errors))

    def test_budget(self):
        big = GOOD + "".join(f"- [L-{i:03d}] x → y (T-1; 2026-01-01)\n" for i in range(10, 170))
        errors = km.lint_memory(big)
        self.assertTrue(any("150" in e for e in errors))


class TestCli(unittest.TestCase):
    def test_lint_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "memory.md"
            p.write_text(GOOD, encoding="utf-8")
            self.assertEqual(km.main(["lint", "--file", str(p)]), 0)
            p.write_text(GOOD.replace("## Уроки\n", ""), encoding="utf-8")
            self.assertEqual(km.main(["lint", "--file", str(p)]), 1)

    def test_write_atomic_replaces_content(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "memory.md"
            p.write_text("old", encoding="utf-8")
            km.write_atomic(p, "new")
            self.assertEqual(p.read_text(encoding="utf-8"), "new")
            self.assertEqual(sorted(os.listdir(d)), ["memory.md"])


class TestLessons(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.p = Path(self.d.name) / "memory.md"
        self.p.write_text(GOOD, encoding="utf-8")

    def test_add_assigns_next_number_and_appends(self):
        code, report = km.add_lesson(self.p, "нет сценария → добавить", "SAS-9", ["cmd/x.go"], "2026-10-24", dry_run=False)
        self.assertEqual(code, 0)
        self.assertIn("[L-005]", report)
        last = self.p.read_text(encoding="utf-8").rstrip().splitlines()[-1]
        self.assertEqual(last, "- [L-005] нет сценария → добавить (SAS-9; 2026-10-24; refs: cmd/x.go)")

    def test_dry_run_does_not_write(self):
        before = self.p.read_text(encoding="utf-8")
        code, report = km.add_lesson(self.p, "a → b", "SAS-9", [], "2026-10-24", dry_run=True)
        self.assertEqual((code, self.p.read_text(encoding="utf-8")), (0, before))
        self.assertTrue(report.startswith("[dry-run]"))

    def test_duplicate_by_text_and_by_refs(self):
        code, report = km.add_lesson(self.p, "Шаг ссылался на `Jobs().Summary`, в коде `Jobs().Info` → сверять сигнатуры с кодом", "SAS-9", [], "2026-10-24", dry_run=True)
        self.assertEqual(code, 2)
        self.assertIn("lesson amend L-003", report)
        code, _ = km.add_lesson(self.p, "другое → другое", "SAS-9", ["pkg/rpc/job.go"], "2026-10-24", dry_run=True)
        self.assertEqual(code, 2)

    def test_amend_replaces_text_and_date(self):
        code, _ = km.amend_lesson(self.p, 4, "новый текст → новый вывод", "2026-10-25", dry_run=False)
        self.assertEqual(code, 0)
        mem = km.parse_memory(self.p.read_text(encoding="utf-8"))
        self.assertEqual((mem.lessons[1].text, mem.lessons[1].date, mem.lessons[1].task),
                         ("новый текст → новый вывод", "2026-10-25", "SAS-201"))
        code, _ = km.add_lesson(self.p, "новый текст → новый вывод", "SAS-9", [], "2026-10-26", dry_run=True)
        self.assertEqual(code, 2)

    def test_add_refuses_broken_file(self):
        self.p.write_text(GOOD.replace("## Ловушки\n", ""), encoding="utf-8")
        code, report = km.add_lesson(self.p, "a → b", "SAS-9", [], "2026-10-24", dry_run=False)
        self.assertEqual(code, 1)
        self.assertIn("## Ловушки", report)

    def test_cli_add_and_amend(self):
        self.assertEqual(km.main(["lesson", "add", "--file", str(self.p), "--text", "a → b", "--task", "SAS-9", "--refs", "x.go,y.go"]), 0)
        self.assertEqual(km.main(["lesson", "amend", "L-005", "--file", str(self.p), "--text", "c → d"]), 0)
        self.assertEqual(km.main(["lesson", "amend", "L-099", "--file", str(self.p), "--text", "c → d"]), 1)


class TestStale(unittest.TestCase):
    def test_reports_only_missing_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".kirpr").mkdir()
            (root / "pkg/rpc").mkdir(parents=True)
            (root / "pkg/rpc/scan.go").write_text("", encoding="utf-8")
            p = root / ".kirpr/memory.md"
            p.write_text(GOOD, encoding="utf-8")
            result = km.stale_refs(p, root)
            self.assertEqual([(l.number, r) for l, r in result], [(3, "pkg/rpc/job.go")])
            self.assertEqual(km.main(["stale", "--file", str(p)]), 0)

    def test_directory_ref_is_not_stale(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".kirpr").mkdir()
            (root / "pkg/rpc").mkdir(parents=True)
            text = GOOD.replace("refs: pkg/rpc/scan.go, pkg/rpc/job.go", "refs: pkg/rpc")
            p = root / ".kirpr/memory.md"
            p.write_text(text, encoding="utf-8")
            self.assertEqual(km.stale_refs(p, root), [])


def make_repo(root, name, branch="main", subjects=()):
    repo = root / name
    repo.mkdir()

    def git(*a):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a],
                       cwd=repo, check=True, capture_output=True)

    git("init", "-q", "-b", branch)
    for i, s in enumerate(subjects or ("init",)):
        (repo / f"f{i}").write_text("x", encoding="utf-8")
        git("add", ".")
        git("commit", "-q", "-m", s)
    return repo


class TestRefresh(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.root = Path(self.d.name)

    def test_scan_detects_branch_and_tracker(self):
        make_repo(self.root, "scansrv", "devel", ["SAS-1 a", "SAS-2 b", "WEB-3 c"])
        make_repo(self.root, "docs-only", "main")
        s = km.scan_workspace(self.root)
        self.assertEqual([(x.name, x.path, x.branch, x.tracker) for x in s],
                         [("docs-only", "./docs-only", "main", ""), ("scansrv", "./scansrv", "devel", "SAS")])

    def test_refresh_creates_and_merges(self):
        make_repo(self.root, "scansrv", "devel", ["SAS-1 a"])
        code, _ = km.refresh_workspace(self.root, "2026-10-24", dry_run=False)
        self.assertEqual(code, 0)
        p = self.root / ".kirpr/workspace.md"
        text = p.read_text(encoding="utf-8")
        self.assertIn("| scansrv | ./scansrv | devel | SAS |  |", text)
        self.assertTrue(text.rstrip().endswith("Обновлено скриптом: 2026-10-24 (`kirpr_memory.py refresh`)"))
        text = text.replace("| scansrv | ./scansrv | devel | SAS |  |",
                            "| scansrv | ./scansrv | devel | SAS | сканирование |\n| legacy | ../legacy | master | SAS | старый |")
        p.write_text(text, encoding="utf-8")
        make_repo(self.root, "upload", "main")
        km.refresh_workspace(self.root, "2026-10-25", dry_run=False)
        text = p.read_text(encoding="utf-8")
        self.assertIn("| scansrv | ./scansrv | devel | SAS | сканирование |", text)
        self.assertIn("| legacy (не найден) | ../legacy | master | SAS | старый |", text)
        self.assertIn("| upload (новый) | ./upload | main |  |  |", text)
        self.assertIn("2026-10-25", text)

    def test_empty_workspace(self):
        code, report = km.refresh_workspace(self.root, "2026-10-24", dry_run=False)
        self.assertEqual(code, 1)
        self.assertIn("сервисы не найдены", report)
        self.assertFalse((self.root / ".kirpr").exists())

    def test_cli_dry_run(self):
        make_repo(self.root, "scansrv")
        self.assertEqual(km.main(["refresh", "--workspace", str(self.root), "--dry-run"]), 0)
        self.assertFalse((self.root / ".kirpr/workspace.md").exists())


RICH = """# Память: scansrv

Вводный абзац, который нельзя терять.

## Как проверять
- `make test`

```bash
## не заголовок, а строка в блоке кода
make lint
```

## Ловушки
- ловушка

## Заметки
- посторонняя секция

## Уроки
- [L-001] a → b (SAS-1; 2026-01-01)
"""


class TestDeltaWrites(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.p = Path(self.d.name) / "memory.md"
        self.p.write_text(RICH, encoding="utf-8")

    def test_add_changes_exactly_one_line(self):
        code, _ = km.add_lesson(self.p, "c → d", "SAS-2", [], "2026-02-02", dry_run=False)
        self.assertEqual(code, 0)
        after = self.p.read_text(encoding="utf-8")
        self.assertEqual(after, RICH + "- [L-002] c → d (SAS-2; 2026-02-02)\n")

    def test_amend_changes_exactly_one_line(self):
        code, _ = km.amend_lesson(self.p, 1, "x → y", "2026-02-02", dry_run=False)
        self.assertEqual(code, 0)
        after = self.p.read_text(encoding="utf-8")
        self.assertEqual(after, RICH.replace("- [L-001] a → b (SAS-1; 2026-01-01)", "- [L-001] x → y (SAS-1; 2026-02-02)"))

    def test_lint_ignores_headings_inside_code_blocks(self):
        self.assertEqual(km.lint_memory(RICH), [])

    def test_add_rejects_values_that_would_break_the_file(self):
        for text, task, refs in (("q → w", "sas-2", []), ("q\nw", "SAS-2", []), ("q → w", "SAS-2", ["f(x).go"])):
            with self.subTest(task=task, text=text, refs=refs):
                code, report = km.add_lesson(self.p, text, task, refs, "2026-02-02", dry_run=False)
                self.assertEqual(code, 1)
                self.assertIn("формат", report)
        self.assertEqual(self.p.read_text(encoding="utf-8"), RICH)
        code, _ = km.add_lesson(self.p, "q → w", "MY_PROJ-7", [], "2026-02-02", dry_run=True)
        self.assertEqual(code, 0)

    def test_add_refuses_to_exceed_budget(self):
        lines = RICH.splitlines()
        filler = [f"- [L-{i:03d}] x → y (TT-1; 2026-01-01)" for i in range(2, 2 + (km.MAX_LINES - len(lines)))]
        self.p.write_text("\n".join(lines + filler) + "\n", encoding="utf-8")
        self.assertEqual(km.lint_memory(self.p.read_text(encoding="utf-8")), [])
        code, report = km.add_lesson(self.p, "z → w", "SAS-2", [], "2026-02-02", dry_run=False)
        self.assertEqual(code, 1)
        self.assertIn("150", report)

    def test_missing_file_gives_message_not_traceback(self):
        missing = Path(self.d.name) / "nope" / "memory.md"
        code, report = km.add_lesson(missing, "a → b", "SAS-2", [], "2026-02-02", dry_run=True)
        self.assertEqual(code, 1)
        self.assertIn("kirpr-onboard", report)
        self.assertEqual(km.main(["lint", "--file", str(missing)]), 1)
        self.assertEqual(km.main(["stale", "--file", str(missing)]), 1)

    def test_argparse_error_exits_1_not_2(self):
        self.assertEqual(km.main(["lint", "--bogus"]), 1)


class TestWorkspaceEdits(unittest.TestCase):
    def test_parse_keeps_pipes_in_role_and_skips_alignment_rows(self):
        text = "| Сервис | Путь | Базовая ветка | Трекер | Роль |\n|:---|:---|:---|:---|:---|\n| a | ./a | main | SAS | RPC | CLI |\n"
        s = km.parse_workspace(text)
        self.assertEqual([(x.name, x.role) for x in s], [("a", "RPC | CLI")])

    def test_merge_keeps_manual_branch(self):
        scanned = [km.Service("a", "./a", "feature-x", "SAS")]
        existing = [km.Service("a", "./a", "develop", "SAS", "роль")]
        merged = km.merge_services(scanned, existing)
        self.assertEqual((merged[0].branch, merged[0].role), ("develop", "роль"))

    def test_init_and_role_commands(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_repo(root, "svc")
            km.refresh_workspace(root, "2026-02-02", dry_run=False)
            self.assertEqual(km.main(["role", "--workspace", str(root), "--service", "svc", "--role", "сканирование"]), 0)
            self.assertIn("| svc | ./svc | main |  | сканирование |", (root / ".kirpr/workspace.md").read_text(encoding="utf-8"))
            self.assertEqual(km.main(["role", "--workspace", str(root), "--service", "nope", "--role", "x"]), 1)
            mem = root / "svc" / ".kirpr" / "memory.md"
            self.assertEqual(km.main(["init", "--file", str(mem), "--name", "svc", "--check", "`make test`", "--traps", "генерёнка", "--dry-run"]), 0)
            self.assertFalse(mem.exists())
            self.assertEqual(km.main(["init", "--file", str(mem), "--name", "svc", "--check", "`make test`", "--traps", "генерёнка"]), 0)
            text = mem.read_text(encoding="utf-8")
            self.assertEqual(km.lint_memory(text), [])
            self.assertIn("# Память: svc\n\n## Как проверять\n- `make test`\n\n## Ловушки\n- генерёнка\n\n## Уроки\n", text)
            self.assertEqual(km.main(["init", "--file", str(mem), "--name", "svc"]), 1)


if __name__ == "__main__":
    unittest.main()
