#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import sys
import time
from typing import Any, NoReturn

TAG = "[ANTISTALL-CODEX]"
VALID_REASONS = {"DONE", "BLOCKED", "QUESTION"}
DEFAULT_BLOCK_CAP = 6
DEFAULT_TICKET_MAX_AGE_S = 300


def codex_home() -> pathlib.Path:
    return pathlib.Path(os.environ.get("CODEX_HOME") or pathlib.Path.home() / ".codex").resolve()


def data_dir() -> pathlib.Path:
    d = codex_home() / "antistall-codex"
    (d / "states").mkdir(parents=True, exist_ok=True)
    (d / "counts").mkdir(parents=True, exist_ok=True)
    return d


def normalize_cwd(cwd: str | None = None) -> str:
    base = pathlib.Path(cwd or os.getcwd())
    try:
        return str(base.resolve()).lower()
    except Exception:
        return str(base.absolute()).lower()


def key_for_cwd(cwd: str | None = None) -> str:
    return hashlib.sha256(normalize_cwd(cwd).encode("utf-8", "replace")).hexdigest()[:24]


def state_path(cwd: str | None = None) -> pathlib.Path:
    return data_dir() / "states" / f"{key_for_cwd(cwd)}.json"


def count_path(cwd: str | None, session_id: str | None) -> pathlib.Path:
    sid = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in (session_id or "unknown"))[:80]
    return data_dir() / "counts" / f"{key_for_cwd(cwd)}-{sid}.txt"


def read_json(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def write_json(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def clear_counts(cwd: str | None = None) -> None:
    prefix = key_for_cwd(cwd) + "-"
    counts = data_dir() / "counts"
    for path in counts.glob(prefix + "*.txt"):
        try:
            path.unlink()
        except Exception:
            pass


def load_state(cwd: str | None = None) -> dict[str, Any]:
    return read_json(state_path(cwd)) or {
        "active": False,
        "cwd": normalize_cwd(cwd),
        "note": "",
        "ticket": None,
        "updated_ts": time.time(),
    }


def save_state(state: dict[str, Any], cwd: str | None = None) -> None:
    state["cwd"] = normalize_cwd(cwd)
    state["updated_ts"] = time.time()
    write_json(state_path(cwd), state)


def print_json(value: dict[str, Any]) -> None:
    print(json.dumps(value, sort_keys=True))


def int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, ""))
    except Exception:
        return default


def hook_continue(system_message: str | None = None) -> NoReturn:
    out: dict[str, Any] = {"continue": True}
    if system_message:
        out["systemMessage"] = system_message
    print_json(out)
    raise SystemExit(0)


def hook_block(reason: str) -> NoReturn:
    print_json({"decision": "block", "reason": reason})
    raise SystemExit(0)


def command_path() -> str:
    return str(pathlib.Path(__file__).resolve())


def install_hook() -> int:
    hooks_path = codex_home() / "hooks.json"
    script = command_path()
    command = f'python "{script}" hook-stop'
    command_windows = f'python "{script}" hook-stop'
    hooks_doc = read_json(hooks_path) if hooks_path.exists() else None
    if hooks_doc is None:
        hooks_doc = {"hooks": {}}
    hooks = hooks_doc.setdefault("hooks", {})
    stop_entries = hooks.setdefault("Stop", [])
    if not isinstance(stop_entries, list):
        print(f"{hooks_path} has hooks.Stop but it is not a list", file=sys.stderr)
        return 3

    found = False
    for entry in stop_entries:
        for hook in entry.get("hooks", []) if isinstance(entry, dict) else []:
            if isinstance(hook, dict) and "antistall.py" in str(hook.get("command", "")):
                hook["type"] = "command"
                hook["command"] = command
                hook["commandWindows"] = command_windows
                hook["timeout"] = 30
                hook["statusMessage"] = "Checking AntiStallCodex sprint gate"
                found = True

    if not found:
        stop_entries.append({
            "hooks": [{
                "type": "command",
                "command": command,
                "commandWindows": command_windows,
                "timeout": 30,
                "statusMessage": "Checking AntiStallCodex sprint gate",
            }]
        })

    if hooks_path.exists():
        backup = hooks_path.with_name(f"hooks.json.bak-{int(time.time())}")
        shutil.copyfile(hooks_path, backup)
        print(f"backed up {hooks_path} -> {backup.name}")
    write_json(hooks_path, hooks_doc)
    print(f"installed AntiStallCodex Stop hook in {hooks_path}")
    print("Next: open /hooks in Codex, review and trust the new hook if prompted.")
    return 0


def arm(note: str) -> int:
    state = load_state()
    state.update({"active": True, "note": note, "armed_ts": time.time(), "ticket": None})
    save_state(state)
    clear_counts()
    print(f"{TAG} armed for {normalize_cwd()}")
    print(f"goal: {note}")
    return 0


def disarm() -> int:
    state = load_state()
    state.update({"active": False, "ticket": None, "disarmed_ts": time.time()})
    save_state(state)
    clear_counts()
    print(f"{TAG} disarmed for {normalize_cwd()}")
    return 0


def ticket(reason: str, detail: str) -> int:
    state = load_state()
    state["ticket"] = {"reason": reason.upper(), "detail": detail, "ts": time.time()}
    save_state(state)
    print(f"{TAG} wrote {reason.upper()} ticket for {normalize_cwd()}: {detail}")
    return 0


def status() -> int:
    state = load_state()
    result = {
        "cwd": normalize_cwd(),
        "state_file": str(state_path()),
        "active": bool(state.get("active")),
        "note": state.get("note", ""),
        "ticket": state.get("ticket"),
        "updated_ts": state.get("updated_ts"),
    }
    print_json(result)
    return 0


def hook_stop() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}

    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else os.getcwd()
    state = load_state(cwd)
    if not state.get("active"):
        return 0

    session_id = payload.get("session_id") if isinstance(payload.get("session_id"), str) else None
    cpath = count_path(cwd, session_id)

    if payload.get("stop_hook_active"):
        state["ticket"] = None
        save_state(state, cwd)
        try:
            cpath.unlink()
        except Exception:
            pass
        hook_continue(f"{TAG} stop allowed by loop guard: this stop was already continued by Stop.")

    max_age = int_env("ANTISTALL_CODEX_TICKET_MAX_AGE_S", DEFAULT_TICKET_MAX_AGE_S)
    ticket_value = state.get("ticket")
    if isinstance(ticket_value, dict):
        state["ticket"] = None
        save_state(state, cwd)
        reason = str(ticket_value.get("reason", "")).upper()
        try:
            age = time.time() - float(ticket_value.get("ts", 0))
        except Exception:
            age = 1e9
        if reason in VALID_REASONS and 0 <= age < max_age:
            if reason == "DONE":
                state["active"] = False
                state["disarmed_ts"] = time.time()
                save_state(state, cwd)
            try:
                cpath.unlink()
            except Exception:
                pass
            hook_continue(f"{TAG} stop allowed: {reason} - {ticket_value.get('detail', '')}")

    cap = int_env("ANTISTALL_CODEX_BLOCK_CAP", DEFAULT_BLOCK_CAP)
    try:
        current = cpath.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        current = "0"
    except Exception:
        hook_continue(f"{TAG} stop allowed: block counter unreadable; failing open.")

    try:
        n = int(current) + 1
    except Exception:
        try:
            cpath.unlink()
        except Exception:
            pass
        hook_continue(f"{TAG} stop allowed: block counter corrupt; failing open.")

    if n >= cap:
        try:
            cpath.unlink()
        except Exception:
            pass
        hook_continue(f"{TAG} anti-loop cap {cap} reached; allowing stop. Check for stale sprint state.")

    try:
        cpath.write_text(str(n), encoding="utf-8")
    except Exception:
        hook_continue(f"{TAG} stop allowed: cannot persist block counter; failing open.")

    note = state.get("note") or "the armed sprint"
    helper_cmd = f'python "{command_path()}"'
    reason = (
        f"{TAG} A sprint is ACTIVE for this project: {note}. You are ending the turn without a fresh "
        "DONE, BLOCKED, or QUESTION ticket. Keep working now. Complete the next concrete step, run relevant "
        "verification when useful, and only stop after writing a ticket with "
        f"`{helper_cmd} done|blocked|question \"<reason>\"`. DONE means the whole authorized queue is complete; "
        "BLOCKED means a human-only decision or external access prevents all useful progress; QUESTION means "
        f"you asked the user and need the answer. Block {n}/{cap}."
    )
    hook_block(reason)
    return 0


def usage() -> int:
    print(
        "Usage: antistall.py install-hook | on <goal> | off | arm <goal> | status | "
        "done <why> | blocked <why> | question <question> | disarm | hook-stop"
    )
    return 2


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return usage()
    cmd = argv[1].lower()
    text = " ".join(argv[2:]).strip()
    if cmd == "install-hook":
        return install_hook()
    if cmd in {"on", "arm"} and text:
        return arm(text)
    if cmd == "status":
        return status()
    if cmd == "done" and text:
        return ticket("DONE", text)
    if cmd == "blocked" and text:
        return ticket("BLOCKED", text)
    if cmd == "question" and text:
        return ticket("QUESTION", text)
    if cmd in {"off", "disarm"}:
        return disarm()
    if cmd == "hook-stop":
        return hook_stop()
    return usage()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
