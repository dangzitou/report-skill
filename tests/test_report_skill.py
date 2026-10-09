import json
import os
import sqlite3
import subprocess
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from report_skill import ai, config, periods, render, summarize
from report_skill.collectors import claude_code, codex, git, zcode
from report_skill.util import clean_prompt, parse_iso, redact

DAY = periods.daily("2026-10-08", 4)


def iso(hour, minute=0):
    """A UTC ISO timestamp that falls on 2026-10-08 local time at the given local hour."""
    local = datetime(2026, 10, 8, hour, minute).astimezone()
    return local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def millis(hour, minute=0):
    return int(datetime(2026, 10, 8, hour, minute).astimezone().timestamp() * 1000)


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


class UtilTests(unittest.TestCase):
    def test_redact_masks_common_secrets(self):
        text = "use sk-ant-abcdefghijklmnop1234 and ghp_" + "a" * 36 + " password=hunter22"
        out = redact(text)
        self.assertNotIn("abcdefghijklmnop1234", out)
        self.assertNotIn("a" * 36, out)
        self.assertIn("password=***", out)

    def test_clean_prompt_drops_agent_noise(self):
        self.assertIsNone(clean_prompt("<command-name>/clear</command-name>"))
        self.assertIsNone(clean_prompt("# AGENTS.md instructions for /x"))
        self.assertIsNone(clean_prompt("<report-skill>\nwrite my report"))
        self.assertEqual(clean_prompt("  fix   the\nlogin bug "), "fix the login bug")

    def test_parse_iso_handles_odd_fractions(self):
        self.assertIsNotNone(parse_iso("2026-10-08T03:05:44.24Z"))
        self.assertIsNotNone(parse_iso("2026-10-08T03:05:44.123456789+00:00"))
        self.assertIsNone(parse_iso("nope"))


class PeriodTests(unittest.TestCase):
    def test_daily_window_starts_at_day_start_hour(self):
        p = periods.daily("2026-10-08", 4)
        self.assertEqual(p.start.hour, 4)
        self.assertEqual(p.end - p.start, timedelta(days=1))

    def test_weekly_is_monday_to_sunday(self):
        p = periods.weekly("2026-10-08", 4)
        self.assertEqual(p.first_day, date(2026, 10, 5))
        self.assertEqual(p.last_day, date(2026, 10, 11))
        self.assertEqual(len(list(p.days)), 7)

    def test_guess_lang(self):
        self.assertEqual(config.guess_lang(["帮我修一下登录接口的超时问题，顺便补测试"]), "zh")
        self.assertEqual(config.guess_lang(["please fix the login timeout and add a regression test"]), "en")


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_claude_code(self):
        write_jsonl(self.tmp / "-proj" / "s1.jsonl", [
            {"type": "custom-title", "customTitle": "Fix login"},
            {"type": "user", "cwd": "/proj", "timestamp": iso(10), "message": {"content": "fix the login bug"}},
            {"type": "user", "cwd": "/proj", "timestamp": iso(10, 1), "isMeta": True, "message": {"content": "meta"}},
            {"type": "user", "cwd": "/proj", "timestamp": iso(10, 2),
             "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
            {"type": "assistant", "cwd": "/proj", "timestamp": iso(10, 3), "message": {"content": [
                {"type": "tool_use", "name": "Edit", "input": {"file_path": "/proj/login.py"}}]}},
            {"type": "user", "cwd": "/proj", "timestamp": iso(2), "message": {"content": "too early"}},
        ])
        [s] = claude_code.collect(DAY.start, DAY.end, self.tmp)
        self.assertEqual(s.title, "Fix login")
        self.assertEqual([p for _, p in s.prompts], ["fix the login bug"])
        self.assertEqual([f for _, f in s.files], ["/proj/login.py"])

    def test_codex(self):
        write_jsonl(self.tmp / "session_index.jsonl", [{"id": "c1", "thread_name": "Add export"}])
        write_jsonl(self.tmp / "sessions" / "2026" / "10" / "08" / "rollout-x.jsonl", [
            {"timestamp": iso(9), "type": "session_meta", "payload": {"id": "c1", "cwd": "/repo"}},
            {"timestamp": iso(9), "type": "response_item", "payload": {
                "type": "message", "role": "user",
                "content": [{"type": "input_text", "text": "<environment_context>x</environment_context>"}]}},
            {"timestamp": iso(9, 1), "type": "response_item", "payload": {
                "type": "message", "role": "user", "content": [{"type": "input_text", "text": "add CSV export"}]}},
            {"timestamp": iso(9, 5), "type": "response_item", "payload": {
                "type": "custom_tool_call", "name": "apply_patch",
                "input": "*** Begin Patch\n*** Update File: src/export.py\n@@\n*** End Patch"}},
        ])
        [s] = codex.collect(DAY.start, DAY.end, self.tmp)
        self.assertEqual(s.title, "Add export")
        self.assertEqual([p for _, p in s.prompts], ["add CSV export"])
        self.assertEqual([f for _, f in s.files], ["/repo/src/export.py"])

    def test_zcode(self):
        db = self.tmp / "cli" / "db" / "db.sqlite"
        db.parent.mkdir(parents=True)
        conn = sqlite3.connect(db)
        conn.executescript("""
            create table session (id text, project_id text, parent_id text, directory text, title text,
                                  time_created integer, time_updated integer);
            create table message (id text, session_id text, time_created integer, data text);
            create table part (id text, message_id text, session_id text, time_created integer, data text);
        """)
        conn.execute("insert into session values ('z1','p',null,'/zrepo','Tune cache',?,?)",
                     (millis(14), millis(15)))
        user = json.dumps({"role": "user", "semantics": {"kind": "user_prompt"}})
        reminder = json.dumps({"role": "user", "semantics": {"kind": "system_reminder"}})
        conn.execute("insert into message values ('m1','z1',?,?)", (millis(14), user))
        conn.execute("insert into message values ('m2','z1',?,?)", (millis(14, 1), reminder))
        conn.execute("insert into part values ('p1','m1','z1',?,?)",
                     (millis(14), json.dumps({"type": "text", "text": "缓存命中率太低，帮我调一下"})))
        conn.execute("insert into part values ('p2','m2','z1',?,?)",
                     (millis(14, 1), json.dumps({"type": "text", "text": "reminder"})))
        conn.execute("insert into part values ('p3','m3','z1',?,?)", (millis(14, 5), json.dumps(
            {"type": "tool", "tool": "Edit", "state": {"input": {"file_path": "/zrepo/cache.go"}}})))
        conn.commit()
        conn.close()
        [s] = zcode.collect(DAY.start, DAY.end, self.tmp)
        self.assertEqual(s.title, "Tune cache")
        self.assertEqual([p for _, p in s.prompts], ["缓存命中率太低，帮我调一下"])
        self.assertEqual([f for _, f in s.files], ["/zrepo/cache.go"])

    def test_git(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        env = dict(os.environ, GIT_AUTHOR_NAME="Ada", GIT_AUTHOR_EMAIL="ada@example.com",
                   GIT_COMMITTER_NAME="Ada", GIT_COMMITTER_EMAIL="ada@example.com",
                   GIT_AUTHOR_DATE=iso(11), GIT_COMMITTER_DATE=iso(11))
        run = lambda *a: subprocess.run(["git", *a], cwd=repo, env=env, check=True, capture_output=True)
        run("init", "-q")
        (repo / "a.txt").write_text("one\ntwo\n")
        run("add", ".")
        run("commit", "-q", "-m", "feat(api): add health check")
        commits = git.collect([str(repo)], DAY.start, DAY.end, ["ada@example.com"])
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0].subject, "feat(api): add health check")
        self.assertEqual(commits[0].insertions, 2)
        self.assertEqual(git.collect([str(repo)], DAY.start, DAY.end, ["someone@else.com"]), [])
        self.assertIn("add health check", render.commit_line(commits[0], "en"))


class EndToEndTests(unittest.TestCase):
    def test_build_render_and_prompt(self):
        tmp = Path(tempfile.mkdtemp())
        write_jsonl(tmp / "claude" / "-p" / "s.jsonl", [
            {"type": "user", "cwd": str(tmp), "timestamp": iso(10), "message": {"content": "write the parser"}},
            {"type": "user", "cwd": str(tmp), "timestamp": iso(10, 20), "message": {"content": "add tests"}},
        ])
        cfg = dict(config.DEFAULTS, sources=["claude-code"], paths={"claude-code": str(tmp / "claude")})
        report = summarize.build(DAY, cfg)
        self.assertEqual(len(report.projects), 1)
        self.assertEqual(report.minutes, 25)
        md = render.draft(report, "zh")
        self.assertIn("工作日报 · 2026-10-08 周四", md)
        self.assertIn("write the parser", md)
        prompt = ai.build_prompt(report, "en", cfg)
        self.assertTrue(prompt.startswith(ai.MARKER))
        self.assertIn("<GUIDE>", prompt)
        self.assertIn("add tests", prompt)

    def test_empty_period(self):
        cfg = dict(config.DEFAULTS, sources=["claude-code"], paths={"claude-code": "/nonexistent"})
        report = summarize.build(DAY, cfg)
        self.assertIn("No agent sessions", render.draft(report, "en"))


if __name__ == "__main__":
    unittest.main()
