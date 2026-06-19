---
name: antistall-codex
description: Install and operate AntiStallCodex, a Codex Stop-hook sprint gate that prevents announce-then-halt drift during approved autonomous work. Use when the user says AntistallON to arm/run the gate, AntistallOFF to turn it off, anti-stall, AntiStallCodex, install anti-stall for Codex, prevent Codex from stopping early, stop drift-stops, keep working until done, or asks to write DONE/BLOCKED/QUESTION stop tickets.
---

# AntiStallCodex

## Purpose

Use Codex's `Stop` hook to keep a session moving while an explicit sprint is armed. A normal instruction such as "do not stop early" is model guidance; a Stop hook is deterministic lifecycle code. When armed and no valid stop ticket exists, the hook returns `decision: "block"` so Codex creates a continuation prompt from the hook reason and keeps working.

This is the Codex port of the AntiStallClaude pattern, adapted to Codex hook semantics.

## Important Codex Differences

- Codex `Stop` hooks use `decision: "block"` to create a continuation prompt. They do not reject or erase the previous assistant message.
- Codex passes `stop_hook_active`; honor it as the primary anti-loop guard.
- Codex may require hook review/trust through `/hooks` before non-managed hooks run.
- Global hooks in `~/.codex/hooks.json` affect all projects, but this skill's hook is inert unless a sprint is armed for the current working directory.

## Desktop App Invocation

The user-facing commands are intentionally simple:

- `AntistallON: <goal>` means arm AntiStallCodex for the current project/session using `<goal>` as the sprint goal.
- `AntistallOFF` means disarm AntiStallCodex for the current project/session.

When the user says `AntistallON`, run the helper with `on` and the user's goal. If no goal is provided, use a concise goal inferred from the current request, such as "finish the current authorized task before stopping."

When the user says `AntistallOFF`, run the helper with `off`.

Examples:

```text
AntistallON: finish the current task completely before stopping.
AntistallOFF
```

## Helper Commands

Run commands from the project directory being worked on:

```powershell
python C:\Users\scott\.codex\skills\antistall-codex\scripts\antistall.py install-hook
python C:\Users\scott\.codex\skills\antistall-codex\scripts\antistall.py on "finish the export pipeline and verify tests"
python C:\Users\scott\.codex\skills\antistall-codex\scripts\antistall.py off
python C:\Users\scott\.codex\skills\antistall-codex\scripts\antistall.py arm "finish the export pipeline and verify tests"
python C:\Users\scott\.codex\skills\antistall-codex\scripts\antistall.py status
python C:\Users\scott\.codex\skills\antistall-codex\scripts\antistall.py done "all requested work is complete and checks passed"
python C:\Users\scott\.codex\skills\antistall-codex\scripts\antistall.py blocked "need the user's production API key"
python C:\Users\scott\.codex\skills\antistall-codex\scripts\antistall.py question "which storage backend should be used?"
python C:\Users\scott\.codex\skills\antistall-codex\scripts\antistall.py disarm
```

Use `on`/`arm` only when the user has approved autonomous work with a clear goal. Use `off`/`disarm` when the user asks to turn it off. Use `done`, `blocked`, or `question` immediately before ending a turn for a legitimate reason.

## Operating Protocol

When a sprint is armed:

1. Keep working until the authorized queue is complete, truly blocked, or a user answer is required.
2. Do not end with a progress summary if concrete authorized work remains.
3. Before stopping legitimately, write exactly one ticket:
   - `done`: all requested work is complete; this disarms the sprint.
   - `blocked`: a human-only decision, credential, external access, or policy choice prevents all remaining useful progress.
   - `question`: a user answer is needed before meaningful progress can continue.
4. If bounced by the Stop hook, follow its continuation prompt and complete the next concrete step.

## Install Or Check The Hook

Run `install-hook` to create or merge the global `~/.codex/hooks.json` Stop hook entry. It is safe to rerun and backs up an existing `hooks.json` before changing it.

After install, the user may need to open `/hooks` in Codex, review the new hook, trust it, and start a fresh thread or reload the app before it fires reliably.

## State

State is stored under `~/.codex/antistall-codex/`, keyed by the normalized working directory. This makes the global hook safe across projects: inactive projects pass through silently.

Use `status` when uncertain. Use `disarm` if a stale sprint should stop enforcing.

## Hook Behavior

The Stop hook must:

- Allow immediately when no sprint is armed for the current `cwd`.
- Allow when `stop_hook_active` is true, clearing any pending ticket and per-session block count.
- Allow and consume a fresh `DONE`, `BLOCKED`, or `QUESTION` ticket.
- Disarm on `DONE`; keep armed on `BLOCKED` and `QUESTION`.
- Block with a concrete continuation prompt when armed and no valid ticket exists.
- Fail open on unreadable or corrupt loop-counter state.

See `references/codex-hooks-notes.md` for source notes and caveats.
