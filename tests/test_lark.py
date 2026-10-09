"""Lark adapter tests against a fake `lark-cli` that mimics its JSON envelopes."""

import json
import os
import stat
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime
from pathlib import Path

from report_skill import ai, config, lark, periods, render, summarize

DAY = periods.daily("2026-10-08", 4)


def at(hour, minute=0, day=8):
    return datetime(2026, 10, day, hour, minute).astimezone().isoformat()


AGENDA = [
    {"event_id": "e1", "summary": "Payment API design review",
     "start_time": {"datetime": at(10)}, "end_time": {"datetime": at(11)}, "self_rsvp_status": "accept"},
    {"event_id": "e2", "summary": "Skipped sync", "start_time": {"datetime": at(15)},
     "end_time": {"datetime": at(16)}, "self_rsvp_status": "decline"},
    {"event_id": "e3", "summary": "Daily standup", "start_time": {"datetime": at(9, 30)},
     "end_time": {"datetime": at(9, 45)}, "self_rsvp_status": "accept"},
]
DONE = {"items": [
    {"guid": "t1", "summary": "Ship refund webhook", "completed": True, "completed_at": at(17)},
    {"guid": "t2", "summary": "Old task", "completed": True, "completed_at": at(17, day=1)},
]}
OPEN = {"items": [
    {"guid": "t3", "summary": "Load-test refund webhook", "completed": False, "due_at": at(12, day=9)},
    {"guid": "t4", "summary": "Write runbook", "completed": False},
]}

FAKE = textwrap.dedent(f"""\
    #!{sys.executable}
    import json, os, sys
    args = sys.argv[1:]
    with open(os.environ["FAKE_LARK_LOG"], "a") as fh:
        fh.write(json.dumps(args) + "\\n")
    if os.environ.get("FAKE_LARK_FAIL"):
        sys.stderr.write(json.dumps({{"ok": False, "error": {{"message": "not logged in",
                                                               "hint": "run lark-cli auth login"}}}}))
        sys.exit(1)
    fixtures = json.load(open(os.environ["FAKE_LARK_FIXTURES"]))
    key = " ".join(args[:2])
    if key == "task +get-my-tasks":
        key += " done" if "--complete=true" in args else " open"
    if key not in fixtures:
        sys.exit(2)
    print(json.dumps({{"ok": True, "identity": "user", "data": fixtures[key]}}))
""")

FIXTURES = {
    "calendar +agenda": AGENDA,
    "task +get-my-tasks done": DONE,
    "task +get-my-tasks open": OPEN,
    "im +messages-send": {"message_id": "om_1"},
    "docs +create": {"document": {"document_id": "doc1", "url": "https://example.feishu.cn/docx/doc1"}},
    "auth status": {"user_name": "Ada"},
    "contact +search-user": {"users": [{"open_id": "ou_me", "name": "Ada"}]},
}


class LarkTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        exe = self.dir / "lark-cli"
        exe.write_text(FAKE)
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
        self.log = self.dir / "calls.log"
        self.old_env = dict(os.environ)
        os.environ["PATH"] = f"{self.dir}{os.pathsep}{os.environ['PATH']}"
        os.environ["FAKE_LARK_LOG"] = str(self.log)
        fixtures = self.dir / "fixtures.json"
        fixtures.write_text(json.dumps(FIXTURES))
        os.environ["FAKE_LARK_FIXTURES"] = str(fixtures)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def cfg(self):
        return dict(config.DEFAULTS, sources=["lark"],
                    lark=dict(config.DEFAULTS["lark"], targets={"leader": "ou_abc"}))

    def test_collect(self):
        warnings = []
        act = lark.collect(DAY.start, DAY.end, self.cfg(), warnings)
        self.assertEqual(warnings, [])
        self.assertEqual([m.summary for m in act.meetings], ["Daily standup", "Payment API design review"])
        self.assertEqual(act.meeting_minutes, 75)
        self.assertEqual([t.summary for t in act.tasks_done], ["Ship refund webhook"])
        self.assertEqual([t.summary for t in act.tasks_open], ["Load-test refund webhook", "Write runbook"])
        agenda = next(c for c in self.calls() if c[:2] == ["calendar", "+agenda"])
        self.assertIn("--start", agenda)
        self.assertIn("json", agenda)

    def test_report_includes_lark(self):
        report = summarize.build(DAY, self.cfg())
        md = render.draft(report, "en")
        self.assertIn("Payment API design review", md)
        self.assertIn("✅ Ship refund webhook", md)
        self.assertIn("1. Load-test refund webhook (due 10-09)", md)
        self.assertIn("2 meetings", md)
        data = summarize.to_dict(report)
        self.assertEqual(len(data["lark"]["meetings"]), 2)
        self.assertIn("tasks_open_due_soon", ai.build_prompt(report, "zh", self.cfg()))

    def test_errors_become_warnings(self):
        os.environ["FAKE_LARK_FAIL"] = "1"
        warnings = []
        act = lark.collect(DAY.start, DAY.end, self.cfg(), warnings)
        self.assertFalse(act)
        self.assertTrue(any("not logged in" in w and "auth login" in w for w in warnings))

    def test_send_and_doc(self):
        target = lark.resolve_target("leader", self.cfg())
        self.assertEqual(target, "ou_abc")
        with self.assertRaises(lark.LarkError):
            lark.resolve_target("bob", self.cfg())
        self.assertEqual(lark.resolve_target("me", self.cfg()), "ou_me")
        self.log.unlink()
        lark.send_message(target, "# hi", "user")
        lark.send_message("oc_team", "# hi", "bot", dry_run=True)
        url = lark.create_doc("Daily", "# hi", "user")
        self.assertEqual(url, "https://example.feishu.cn/docx/doc1")
        send1, send2, doc = self.calls()
        self.assertEqual(send1[:6], ["im", "+messages-send", "--as", "user", "--user-id", "ou_abc"])
        self.assertIn("--markdown", send1)
        self.assertIn("--chat-id", send2)
        self.assertIn("--dry-run", send2)
        self.assertEqual(doc[doc.index("--doc-format") + 1], "markdown")

    def test_status(self):
        self.assertEqual(lark.status(), "logged in as Ada")


if __name__ == "__main__":
    unittest.main()
