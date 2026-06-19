# AntiStallCodex

A Codex Desktop Stop-hook sprint gate that keeps autonomous work from ending early.

Version 0.1.0 - MIT licensed - built for Codex Desktop and Codex hooks

[Landing page](https://scottconverse.github.io/antistallcodex/)

AntiStallCodex is the Codex-specific sibling of AntiStallClaude. It uses Codex's `Stop` hook to prevent the announce-then-halt failure: the agent says what it will do next, writes a tidy progress summary, and then stops with authorized work still sitting on the table.

## The short version

In Codex Desktop, say:

```text
AntistallON: finish this task completely before stopping.
```

To turn it off:

```text
AntistallOFF
```

That is the intended interface. The Python helper exists so Codex can wire the hook and maintain state.

## How it works

Codex supports lifecycle hooks. `Stop` runs when a turn is about to stop. If a Stop hook returns:

```json
{
  "decision": "block",
  "reason": "Keep working..."
}
```

Codex creates a continuation prompt from `reason` and keeps going.

AntiStallCodex installs a global Stop hook inline in `~/.codex/config.toml`. The hook is inert unless a sprint has been armed for the current project directory. Once armed, Codex can stop only by writing a fresh one-use ticket:

- `DONE` - the whole authorized queue is complete and the sprint disarms
- `BLOCKED` - a human-only decision or external access blocks all useful progress
- `QUESTION` - Codex asked the user something and needs the answer

## Install

Clone and run:

```bash
git clone https://github.com/scottconverse/antistallcodex.git
python antistallcodex/install.py
```

Then in Codex Desktop, open `/hooks` and trust the AntiStallCodex hook if prompted. Hooks may require a fresh thread or app reload before they fire.

The installer:

- copies `skill/antistall-codex/` into `~/.codex/skills/antistall-codex/`
- writes or merges a global `~/.codex/config.toml` Stop hook
- leaves the hook inert until `AntistallON` is used in a project

## Desktop usage

Start an enforced sprint:

```text
AntistallON: finish the installer fixes, run tests, and report only when done.
```

Turn it off:

```text
AntistallOFF
```

Mark a legitimate stop:

```text
Done: all requested work is complete and verified.
```

or:

```text
Blocked: I need Scott to choose the release target.
```

or:

```text
Question: should this support Windows only or all platforms?
```

The skill teaches Codex to map those plain-language requests to the helper's ticket commands.

## Helper commands

You usually do not type these yourself in Codex Desktop. Codex can run them for you.

```bash
python ~/.codex/skills/antistall-codex/scripts/antistall.py on "finish this sprint"
python ~/.codex/skills/antistall-codex/scripts/antistall.py off
python ~/.codex/skills/antistall-codex/scripts/antistall.py status
python ~/.codex/skills/antistall-codex/scripts/antistall.py done "complete"
python ~/.codex/skills/antistall-codex/scripts/antistall.py blocked "need credentials"
python ~/.codex/skills/antistall-codex/scripts/antistall.py question "which option?"
```

On Windows the same script lives under:

```text
%USERPROFILE%\.codex\skills\antistall-codex\scripts\antistall.py
```

## Safety

AntiStallCodex is intentionally fail-open.

- If no sprint is armed, the hook returns `{"continue": true}`.
- If `stop_hook_active` is true, the hook allows the stop so it cannot loop on its own continuation.
- If the per-session block counter is unreadable, corrupt, or unwritable, the hook allows the stop.
- If the block cap is reached, the hook allows the stop and reports stale sprint state.

This protects against token-burning continuation loops.

## State

State lives under:

```text
~/.codex/antistall-codex/
```

Sprints are keyed by normalized current working directory, so one global hook can protect many projects without affecting inactive ones.

## Limitations

- Codex must load and trust the hook. If hooks are disabled or untrusted, AntiStallCodex cannot enforce anything.
- `Stop` hook continuation depends on Codex's hook implementation. Some Codex releases have had hook UI or continuation bugs; see `docs/MANUAL.md`.
- This enforces "do not stop early"; it does not prove the work is correct. Pair it with tests, audits, and review.
- The agent can still write a false `DONE` ticket. That changes a passive silent drift into an explicit, logged claim.

## Verify

Run the unit tests:

```bash
python tests/test_antistall.py
```

Behavioral test inside Codex Desktop:

1. Use `AntistallON: gate test`.
2. Ask Codex to stop with work remaining.
3. The Stop hook should continue the session with an AntiStallCodex message.
4. Use `AntistallOFF` after the test.

## Removal

Delete `~/.codex/skills/antistall-codex/`, remove the marked AntiStallCodex block from `~/.codex/config.toml`, and optionally delete `~/.codex/antistall-codex/`.

## License

MIT - see `LICENSE`.
