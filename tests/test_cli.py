"""CLI behaviour that agents depend on: setup, config, send, exit codes, JSON output."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from report_skill import cli, config
from tests.test_lark import FAKE, FIXTURES


def run(argv, stdin=""):
    out, err = io.StringIO(), io.StringIO()
    old_stdin = os.sys.stdin
    os.sys.stdin = io.StringIO(stdin)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = cli.main(argv)
            except SystemExit as e:
                code = e.code
    finally:
        os.sys.stdin = old_stdin
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self):
        self.old_env = dict(os.environ)
        self.home = Path(tempfile.mkdtemp())
        os.environ["HOME"] = str(self.home)
        os.environ["REPORT_SKILL_CONFIG"] = str(self.home / "cfg.json")
        # fake lark-cli on PATH
        bindir = self.home / "bin"
        bindir.mkdir()
        exe = bindir / "lark-cli"
        exe.write_text(FAKE)
        exe.chmod(0o755)
        (self.home / "fx.json").write_text(json.dumps(FIXTURES))
        os.environ["PATH"] = f"{bindir}{os.pathsep}{os.environ['PATH']}"
        os.environ["FAKE_LARK_LOG"] = str(self.home / "log")
        os.environ["FAKE_LARK_FIXTURES"] = str(self.home / "fx.json")
        self.report = self.home / "report.md"
        self.report.write_text("# 工作日报\n\n- 修复导出超时\n")

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)

    def test_setup_installs_skill_everywhere_and_is_idempotent(self):
        (self.home / ".claude").mkdir()
        (self.home / ".codex").mkdir()
        for _ in range(2):
            code, out, _ = run(["setup", "--json"])
            self.assertEqual(code, 0)
        info = json.loads(out)
        self.assertEqual({s["agent"] for s in info["skills"]}, {"Claude Code", "Codex"})
        self.assertTrue((self.home / ".claude/skills/report-skill/SKILL.md").exists())
        self.assertTrue((self.home / ".codex/skills/report-skill/references/guide.zh.md").exists())
        self.assertFalse(info["config_created"])  # second run keeps the existing config
        self.assertIn("next_steps", info)

    def test_setup_custom_dir_and_aliases(self):
        code, out, _ = run(["install-skill", "--skills-dir", str(self.home / "my-skills")])
        self.assertEqual(code, 0)
        self.assertTrue((self.home / "my-skills/report-skill/SKILL.md").exists())

    def test_config_set_get_unset(self):
        run(["config", "set", "lark.targets.leader", "ou_1"])
        run(["config", "set", "sources", '["git", "lark"]'])
        self.assertEqual(run(["config", "get", "lark.targets.leader"])[1].strip(), "ou_1")
        cfg = config.load()
        self.assertEqual(cfg["sources"], ["git", "lark"])
        self.assertEqual(cfg["lark"]["identity"], "user")  # nested defaults survive a partial block
        run(["config", "unset", "lark.targets.leader"])
        self.assertEqual(run(["config", "get", "lark.targets.leader"])[1].strip(), "null")

    def test_send_needs_approval_for_others(self):
        code, out, _ = run(["send", str(self.report), "--to-lark", "ou_boss", "--json"])
        self.assertEqual(code, cli.EXIT_NEEDS_OK)
        self.assertFalse(json.loads(out)["sent"])
        self.assertFalse((self.home / "log").exists() and "+messages-send" in (self.home / "log").read_text())

        code, out, _ = run(["send", str(self.report), "--to-lark", "ou_boss", "--yes", "--json"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["sent"])

    def test_send_to_me_and_doc_from_stdin(self):
        code, out, _ = run(["send", "-", "--to-lark", "me", "--lark-doc", "--json"], stdin="# Daily\n- done\n")
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertTrue(result["sent"])
        self.assertEqual(result["target"]["id"], "ou_me")
        self.assertTrue(result["doc_url"].startswith("https://"))

    def test_send_default_target_from_config(self):
        run(["config", "set", "lark.targets.leader", "ou_lead"])
        run(["config", "set", "lark.send_to", "leader"])
        code, out, _ = run(["send", str(self.report), "--to-lark", "--yes", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["target"], {"name": "leader", "id": "ou_lead"})

    def test_send_errors_are_machine_readable(self):
        code, out, _ = run(["send", str(self.report), "--to-lark", "nobody", "--json"])
        self.assertEqual(code, 1)
        self.assertIn("error", json.loads(out))
        os.environ["PATH"] = "/usr/bin:/bin"
        code, out, _ = run(["send", str(self.report), "--lark-doc", "--json"])
        self.assertEqual(code, 1)
        self.assertIn("fix", json.loads(out))

    def test_usage_errors(self):
        self.assertEqual(run(["send", str(self.report)])[0], 2)
        self.assertEqual(run(["not-a-date"])[0], 2)


if __name__ == "__main__":
    unittest.main()
