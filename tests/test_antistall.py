from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "antistall-codex" / "scripts" / "antistall.py"


class AntiStallCodexTests(unittest.TestCase):
    def run_cmd(self, args, cwd, codex_home, stdin=None):
        env = os.environ.copy()
        env["CODEX_HOME"] = str(codex_home)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=cwd,
            env=env,
            input=stdin,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def payload(self, cwd, active=False):
        return json.dumps({
            "session_id": "test-session",
            "cwd": str(cwd),
            "hook_event_name": "Stop",
            "turn_id": "turn-1",
            "stop_hook_active": active,
            "last_assistant_message": "summary",
        })

    def test_inactive_hook_is_silent(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cwd:
            result = self.run_cmd(["hook-stop"], cwd, pathlib.Path(home), self.payload(cwd))
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")

    def test_on_off_aliases_change_state(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cwd:
            result = self.run_cmd(["on", "ship", "the", "thing"], cwd, pathlib.Path(home))
            self.assertEqual(result.returncode, 0, result.stderr)
            status = self.run_cmd(["status"], cwd, pathlib.Path(home))
            self.assertTrue(json.loads(status.stdout)["active"])

            result = self.run_cmd(["off"], cwd, pathlib.Path(home))
            self.assertEqual(result.returncode, 0, result.stderr)
            status = self.run_cmd(["status"], cwd, pathlib.Path(home))
            self.assertFalse(json.loads(status.stdout)["active"])

    def test_armed_hook_blocks_then_loop_guard_allows(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cwd:
            home_path = pathlib.Path(home)
            self.run_cmd(["on", "finish validation"], cwd, home_path)
            result = self.run_cmd(["hook-stop"], cwd, home_path, self.payload(cwd))
            self.assertEqual(result.returncode, 0)
            out = json.loads(result.stdout)
            self.assertEqual(out["decision"], "block")
            self.assertIn("finish validation", out["reason"])

            result = self.run_cmd(["hook-stop"], cwd, home_path, self.payload(cwd, active=True))
            self.assertEqual(result.returncode, 0)
            out = json.loads(result.stdout)
            self.assertTrue(out["continue"])
            self.assertIn("loop guard", out["systemMessage"])

    def test_done_ticket_disarms(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cwd:
            home_path = pathlib.Path(home)
            self.run_cmd(["on", "finish validation"], cwd, home_path)
            self.run_cmd(["done", "complete"], cwd, home_path)
            result = self.run_cmd(["hook-stop"], cwd, home_path, self.payload(cwd))
            self.assertEqual(result.returncode, 0)
            out = json.loads(result.stdout)
            self.assertTrue(out["continue"])
            self.assertIn("DONE", out["systemMessage"])

            status = self.run_cmd(["status"], cwd, home_path)
            self.assertFalse(json.loads(status.stdout)["active"])

    def test_install_hook_writes_global_hooks_json(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cwd:
            home_path = pathlib.Path(home)
            result = self.run_cmd(["install-hook"], cwd, home_path)
            self.assertEqual(result.returncode, 0, result.stderr)
            hooks = json.loads((home_path / "hooks.json").read_text(encoding="utf-8"))
            stop_hooks = hooks["hooks"]["Stop"]
            command = stop_hooks[0]["hooks"][0]["command"]
            self.assertIn("antistall.py", command)


if __name__ == "__main__":
    unittest.main()
