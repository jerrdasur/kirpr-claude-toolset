from pathlib import Path
import os
import subprocess
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ALL_SKILLS = (
    "kirpr-task-fetch", "kirpr-task-create", "kirpr-task-update",
    "kirpr-task-delete", "kirpr-tasks-decompose", "kirpr-tasks-review",
    "kirpr-tasks-adapt", "kirpr-tasks-push", "kirpr-adr-init",
    "kirpr-adr-write", "kirpr-adr-review", "kirpr-text",
    "expert-panel", "grill-me", "kirpr-flow",
)


class InstallerCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.input_file = self.root / "input"
        self.input_file.write_text("3\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self, script, *args, check=True, extra_env=None, with_input=True):
        env = os.environ.copy()
        env["KIRPR_INSTALL_ROOT"] = str(self.root)
        if with_input:
            env["KIRPR_INPUT_FILE"] = str(self.input_file)
        else:
            env["KIRPR_INPUT_FILE"] = str(self.root / "missing-input")
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [str(ROOT / script), *args], cwd=ROOT, env=env,
            text=True, capture_output=True, check=check,
        )


class TestCleanInstall(InstallerCase):
    def assert_skills(self, base):
        for name in ALL_SKILLS:
            self.assertTrue((base / name / "SKILL.md").is_file(), name)
            self.assertTrue((base / name / "agents" / "openai.yaml").is_file(), name)

    def manifest_records(self):
        manifest = self.root / ".config" / "kirpr" / "install-manifest"
        return {tuple(line.split("\t")) for line in manifest.read_text(encoding="utf-8").splitlines()}

    def test_codex_target(self):
        self.run_script("install.sh", "--target", "codex")
        self.assert_skills(self.root / ".agents" / "skills")
        self.assertFalse((self.root / ".claude" / "skills").exists())
        self.assertFalse((self.root / ".claude" / "commands" / "kirpr").exists())
        records = self.manifest_records()
        self.assertIn(("target", "codex"), records)
        self.assertIn(("path", "codex", str(self.root / ".agents" / "skills")), records)
        self.assertIn(("path", "shared", str(self.root / ".local" / "share" / "kirpr")), records)
        self.assertFalse(any(record[1] == "claude" for record in records if len(record) > 1))

    def test_claude_target(self):
        self.run_script("install.sh", "--target", "claude")
        self.assert_skills(self.root / ".claude" / "skills")
        self.assertEqual(len(list((self.root / ".claude" / "commands" / "kirpr").glob("*.md"))), 12)
        self.assertFalse((self.root / ".agents" / "skills").exists())
        records = self.manifest_records()
        self.assertIn(("target", "claude"), records)
        self.assertIn(("path", "claude", str(self.root / ".claude" / "skills")), records)
        self.assertIn(("path", "claude", str(self.root / ".claude" / "commands" / "kirpr")), records)
        self.assertFalse(any(record[1] == "codex" for record in records if len(record) > 1))

    def test_all_target(self):
        self.run_script("install.sh", "--target", "all")
        self.assert_skills(self.root / ".agents" / "skills")
        self.assert_skills(self.root / ".claude" / "skills")
        self.assertTrue((self.root / ".local" / "share" / "kirpr" / "scripts" / "manage_jira.py").is_file())

    def test_interactive_target_selection(self):
        self.input_file.write_text("2\n3\n", encoding="utf-8")
        self.run_script("install.sh")
        self.assert_skills(self.root / ".agents" / "skills")
        self.assertFalse((self.root / ".claude" / "skills").exists())

    def test_no_target_without_input_terminal_fails(self):
        result = self.run_script("install.sh", check=False, with_input=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--target", result.stderr)
        self.assertFalse((self.root / ".agents").exists())

    def test_tracker_input_failure_leaves_no_destinations(self):
        result = self.run_script(
            "install.sh", "--target", "codex", check=False, with_input=False
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / ".config").exists())
        self.assertFalse((self.root / ".local").exists())
        self.assertFalse((self.root / ".agents").exists())
        self.assertFalse((self.root / ".claude").exists())
        self.assertFalse((self.root / ".config" / "kirpr" / "install-manifest").exists())

    def test_unknown_target_fails_without_writes(self):
        result = self.run_script("install.sh", "--target", "other", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / ".agents").exists())
        self.assertIn("claude|codex|all", result.stderr)

    def test_tracker_choice_writes_shared_user_configuration(self):
        self.input_file.write_text(
            "1\n1\nhttps://youtrack.example.test\n", encoding="utf-8"
        )
        self.run_script("install.sh")
        tracker = self.root / ".config" / "kirpr" / "tracker.md"
        self.assertTrue(tracker.is_file())
        text = tracker.read_text(encoding="utf-8")
        self.assertTrue("Трекер: YouTrack" in text)
        self.assertNotIn("Скрипт:", text)
        self.assertNotIn(".claude", text)


class TestMigrationAndUninstall(InstallerCase):
    def seed(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_migrates_and_normalizes_claude_tracker(self):
        self.seed(
            ".claude/kirpr/config/tracker.md",
            "Трекер: Jira\nСкрипт: `python3 ~/.claude/kirpr/scripts/fetch_jira.py X`\n"
            "URL: https://jira/browse/X\n",
        )
        self.run_script("install.sh", "--target", "codex")
        text = (self.root / ".config/kirpr/tracker.md").read_text(encoding="utf-8")
        self.assertIn("Трекер: Jira", text)
        self.assertNotIn("Скрипт:", text)
        self.assertNotIn(".claude", text)

    def test_conflicting_custom_experts_stop_before_skill_replacement(self):
        self.seed(".config/kirpr/custom-experts.md", "shared\n")
        self.seed(".claude/skills/expert-panel/custom-experts.md", "claude\n")
        marker = self.seed(".agents/skills/expert-panel/marker", "original\n")
        result = self.run_script("install.sh", "--target", "codex", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(encoding="utf-8"), "original\n")

    def test_backs_up_displaced_codex_skills_and_retired_adr(self):
        self.seed(".agents/skills/kirpr-text/old", "text\n")
        self.seed(".agents/skills/kirpr-adr/SKILL.md", "legacy adr\n")
        self.run_script("install.sh", "--target", "codex")
        backups = list((self.root / ".config/kirpr/backups").rglob("old"))
        self.assertEqual(len(backups), 1)
        self.assertFalse((self.root / ".agents/skills/kirpr-adr").exists())

    def test_reinstall_preserves_user_files(self):
        self.run_script("install.sh", "--target", "all")
        custom = self.seed(".config/kirpr/custom-experts.md", "mine\n")
        self.run_script("install.sh", "--target", "all")
        self.assertEqual(custom.read_text(encoding="utf-8"), "mine\n")

    def test_uninstall_codex_leaves_claude_runtime_and_config(self):
        self.run_script("install.sh", "--target", "all")
        self.run_script("uninstall.sh", "--target", "codex")
        self.assertFalse((self.root / ".agents/skills/kirpr-text").exists())
        self.assertTrue((self.root / ".claude/skills/kirpr-text").exists())
        self.assertTrue((self.root / ".local/share/kirpr").exists())
        self.assertTrue((self.root / ".config/kirpr").exists())

    def test_failed_install_rolls_back_and_keeps_old_manifest(self):
        marker = self.seed(".agents/skills/kirpr-text/marker", "original\n")
        manifest = self.seed(".config/kirpr/install-manifest", "version\t1\n")
        result = self.run_script(
            "install.sh", "--target", "codex", check=False,
            extra_env={"KIRPR_TEST_FAIL_AFTER_INSTALL": "1"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(encoding="utf-8"), "original\n")
        self.assertEqual(manifest.read_text(encoding="utf-8"), "version\t1\n")

    def test_rejects_untrusted_manifest_before_uninstall_mutation(self):
        victim = self.seed("not-managed", "keep\n")
        manifest = self.seed(
            ".config/kirpr/install-manifest",
            "version\t1\ntarget\tcodex\n"
            f"path\tcodex\t{victim}\n",
        )
        result = self.run_script("uninstall.sh", "--target", "codex", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(victim.read_text(encoding="utf-8"), "keep\n")
        self.assertIn("Invalid install manifest", result.stderr)
        self.assertTrue(manifest.exists())

    def test_rejects_untrusted_backup_record_before_uninstall_mutation(self):
        skill = self.seed(".agents/skills/kirpr-text/marker", "keep\n")
        outside_backup = self.seed("not-a-backup", "keep\n")
        self.seed(
            ".config/kirpr/install-manifest",
            "version\t1\ntarget\tcodex\n"
            f"path\tcodex\t{self.root / '.agents/skills/kirpr-text'}\n"
            f"backup\tcodex\t{self.root / '.agents/skills/kirpr-text'}\t{outside_backup}\n",
        )
        result = self.run_script("uninstall.sh", "--target", "codex", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(skill.read_text(encoding="utf-8"), "keep\n")
        self.assertTrue(outside_backup.exists())

    def test_last_uninstall_keeps_runtime_without_shared_manifest_record(self):
        self.run_script("install.sh", "--target", "codex")
        manifest = self.root / ".config/kirpr/install-manifest"
        manifest.write_text(
            "\n".join(
                line for line in manifest.read_text(encoding="utf-8").splitlines()
                if not line.startswith("path\tshared\t")
            ) + "\n",
            encoding="utf-8",
        )
        self.run_script("uninstall.sh", "--target", "codex")
        self.assertTrue((self.root / ".local/share/kirpr").exists())

    def test_final_uninstall_restores_shared_runtime_backup(self):
        self.seed(".local/share/kirpr/marker", "original runtime\n")
        self.input_file.write_text("3\n", encoding="utf-8")
        self.run_script("install.sh", "--target", "codex")
        self.input_file.write_text("y\n", encoding="utf-8")
        self.run_script("uninstall.sh", "--target", "codex")
        marker = self.root / ".local/share/kirpr/marker"
        self.assertEqual(marker.read_text(encoding="utf-8"), "original runtime\n")

    def test_all_uninstall_prompts_once_and_restores_all_target_backups(self):
        self.seed(".agents/skills/kirpr-text/marker", "codex original\n")
        self.seed(".claude/skills/kirpr-text/marker", "claude original\n")
        self.input_file.write_text("3\n", encoding="utf-8")
        self.run_script("install.sh", "--target", "all")
        self.input_file.write_text("y\n", encoding="utf-8")
        result = self.run_script("uninstall.sh", "--target", "all")
        self.assertEqual(result.stdout.count("Restore displaced content"), 1)
        self.assertEqual(
            (self.root / ".agents/skills/kirpr-text/marker").read_text(encoding="utf-8"),
            "codex original\n",
        )
        self.assertEqual(
            (self.root / ".claude/skills/kirpr-text/marker").read_text(encoding="utf-8"),
            "claude original\n",
        )

    def test_backups_do_not_collide_within_one_second(self):
        self.seed(".agents/skills/kirpr-text/old", "first\n")
        self.input_file.write_text("3\n3\n", encoding="utf-8")
        self.run_script("install.sh", "--target", "codex")
        self.seed(".agents/skills/kirpr-adr/SKILL.md", "second\n")
        self.run_script("install.sh", "--target", "codex")
        backups = self.root / ".config/kirpr/backups"
        self.assertEqual(len([path for path in backups.iterdir() if path.is_dir()]), 2)

    def test_later_failure_restores_preexisting_replaced_skill(self):
        marker = self.seed(".agents/skills/kirpr-text/marker", "original\n")
        self.seed(".config/kirpr/install-manifest", "version\t1\n")
        result = self.run_script(
            "install.sh", "--target", "codex", check=False,
            extra_env={"KIRPR_TEST_FAIL_AFTER_SKILL": "kirpr-flow"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(encoding="utf-8"), "original\n")


class TestRemoteInstall(InstallerCase):
    def test_archive_delegates_target(self):
        archive = self.root / "kirpr.tar.gz"
        archive_root = "kirpr-claude-toolset-main"
        with tarfile.open(archive, "w:gz") as tar:
            for name in ("install.sh", "installer", "skills", "commands", "kirpr"):
                tar.add(ROOT / name, arcname=f"{archive_root}/{name}")

        curl = self.root / "curl"
        curl.write_text(
            "#!/usr/bin/env bash\n"
            "set -eu\n"
            "destination=\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            "    case \"$1\" in\n"
            "        -o) destination=\"$2\"; shift 2 ;;\n"
            "        *) shift ;;\n"
            "    esac\n"
            "done\n"
            "[ -n \"$destination\" ]\n"
            "cp \"$KIRPR_TEST_ARCHIVE\" \"$destination\"\n",
            encoding="utf-8",
        )
        curl.chmod(0o755)

        self.run_script(
            "install-remote.sh", "--target", "codex",
            extra_env={
                "KIRPR_CURL_BIN": str(curl),
                "KIRPR_TEST_ARCHIVE": str(archive),
            },
        )

        self.assertTrue((self.root / ".agents/skills/kirpr-task-fetch/SKILL.md").is_file())
        self.assertFalse((self.root / ".claude/skills").exists())
