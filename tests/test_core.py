import json
import tempfile
import unittest
from pathlib import Path

from dirlint.core import DEFAULTS, deep_merge, scan


def make_config(**overrides):
    base = {
        "allowedTop": ["projects", "tools", "workspace", "archive", "cache"],
        "zones": {
            "projects": ["projects"],
            "tools": ["tools"],
            "workspace": ["workspace"],
            "archive": ["archive"],
            "cache": ["cache"],
        },
        "workspaceAllowed": ["temp", "temp-workspace"],
        "retired": ["retired-tool"],
        "scan": {"maxDepth": 4},
        "duplicates": {"minBytes": 10},
    }
    return deep_merge(deep_merge(DEFAULTS, base), overrides)


class DirLintTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def touch(self, rel, content="x"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def rules_of(self, result):
        return {f.rule for f in result.findings}

    def test_clean_tree_passes(self):
        self.touch("projects/demo/README.md", "readme")
        self.touch("workspace/temp-workspace/task-a/README.md", "task")
        result = scan(self.root, make_config())
        self.assertEqual([], result.findings)

    def test_top_level_whitelist(self):
        (self.root / "stray-dir").mkdir()
        self.touch("stray.log", "log")
        result = scan(self.root, make_config())
        rels = {f.rel for f in result.findings if f.rule == "R0"}
        self.assertIn("stray-dir", rels)
        self.assertIn("stray.log", rels)

    def test_same_name_nesting(self):
        self.touch("tools/tools/bin/tool.exe", "bin")
        result = scan(self.root, make_config())
        self.assertIn("R1", self.rules_of(result))

    def test_project_root_stray_file(self):
        self.touch("projects/demo/server.log", "log")
        result = scan(self.root, make_config())
        self.assertIn("R2", self.rules_of(result))

    def test_backup_directory(self):
        self.touch("projects/demo/backup-20260101/x.txt", "x")
        result = scan(self.root, make_config())
        self.assertIn("R3", self.rules_of(result))

    def test_temp_directory_in_project(self):
        self.touch("projects/demo/tmp/x.txt", "x")
        result = scan(self.root, make_config())
        self.assertIn("R4", self.rules_of(result))

    def test_workspace_unregistered_directory(self):
        (self.root / "workspace" / "2026-01-01-00-00").mkdir(parents=True)
        result = scan(self.root, make_config())
        self.assertIn("R5", self.rules_of(result))

    def test_retired_directory(self):
        (self.root / "retired-tool").mkdir()
        result = scan(self.root, make_config())
        self.assertIn("R6", self.rules_of(result))

    def test_duplicates_opt_in(self):
        self.touch("projects/a/data.bin", "same-content")
        self.touch("projects/b/data-copy.bin", "same-content")
        cfg = make_config()
        cfg["rules"]["duplicates"] = True
        result = scan(self.root, cfg)
        self.assertIn("R7", self.rules_of(result))
        dup = next(f for f in result.findings if f.rule == "R7")
        self.assertGreater(dup.size, 0)

    def test_size_uses_directory_total(self):
        self.touch("projects/demo/backup-20260101/a.bin", "a" * 100)
        self.touch("projects/demo/backup-20260101/b.bin", "b" * 200)
        result = scan(self.root, make_config())
        backup = next(f for f in result.findings if f.rule == "R3")
        self.assertGreaterEqual(backup.size, 300)


if __name__ == "__main__":
    unittest.main()
