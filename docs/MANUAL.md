# AntiStallCodex Manual

## Runtime support

AntiStallCodex targets Codex's documented hook system, specifically the `Stop` event. The hook contract used here:

- Stop hooks receive JSON on stdin.
- Payload includes `cwd`, `session_id`, `turn_id`, `stop_hook_active`, and `last_assistant_message`.
- Stop hooks must emit JSON on stdout.
- Returning `{"decision":"block","reason":"..."}` asks Codex to continue by creating a new continuation prompt from `reason`.

This is not the same as a normal notification. It is part of Codex's agent lifecycle.

## Why the hook is global

Codex can load hooks from global, project-local, and plugin locations. AntiStallCodex installs globally because it is intended to be available in every Codex Desktop project.

The global hook is safe because it checks per-project armed state before doing anything. If the current project has not been armed with `AntistallON`, the hook exits with no output.

## State model

All state lives under `~/.codex/antistall-codex/`.

Each project state file contains:

```json
{
  "active": true,
  "cwd": "normalized project path",
  "note": "sprint goal",
  "ticket": null,
  "updated_ts": 1234567890
}
```

Tickets are embedded in the state file:

```json
{
  "reason": "DONE",
  "detail": "all work complete",
  "ts": 1234567890
}
```

Tickets are consumed once. Stale tickets are ignored.

## Loop safety

A Stop hook that keeps returning `decision: "block"` can create an infinite continuation loop. AntiStallCodex uses two guards:

1. `stop_hook_active` from Codex is the primary guard. If true, the hook allows the stop.
2. A per-project, per-session block counter is the secondary guard. If the cap is reached, the hook allows the stop.

Any uncertainty in the counter fails open.

## Trust and review

Codex requires non-managed hooks to be reviewed and trusted. After installing, open `/hooks` in Codex Desktop and trust the AntiStallCodex hook if it appears as pending.

If the hook does not fire:

- Check `~/.codex/hooks.json`.
- Check that hooks are enabled in Codex config.
- Check `/hooks` trust state.
- Start a fresh thread or reload Codex Desktop.
- Run `python ~/.codex/skills/antistall-codex/scripts/antistall.py status` from the target project to confirm the sprint is armed.

## Known caveats

Community reports have noted that some Codex releases had Stop hook UI detail issues and occasional continuation edge cases. AntiStallCodex keeps the hook payload simple and the anti-loop cap conservative to reduce those risks.

## Desktop command mapping

The skill maps these user phrases:

- `AntistallON: <goal>` -> helper `on <goal>`
- `AntistallOFF` -> helper `off`
- `Done: <reason>` -> helper `done <reason>`
- `Blocked: <reason>` -> helper `blocked <reason>`
- `Question: <question>` -> helper `question <question>`

The helper also supports explicit `arm`, `disarm`, and `status` for internal use.
