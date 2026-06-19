# Codex Hook Notes

Official Codex hook behavior relevant to AntiStallCodex:

- Hooks are enabled by default unless `[features].hooks = false`.
- Codex discovers hooks in `~/.codex/hooks.json`, `~/.codex/config.toml`, `<repo>/.codex/hooks.json`, `<repo>/.codex/config.toml`, and enabled plugins.
- Non-managed command hooks must be reviewed and trusted before running.
- `Stop` hook input includes `session_id`, `cwd`, `hook_event_name`, `turn_id`, `stop_hook_active`, and `last_assistant_message`.
- `Stop` expects JSON on stdout. To continue the session, return:

```json
{
  "decision": "block",
  "reason": "Run one more pass over the failing tests."
}
```

- For `Stop`, `decision: "block"` creates a new continuation prompt using `reason`.
- If any matching `Stop` hook returns `continue: false`, that takes precedence over continuation decisions from other matching hooks.
- Multiple matching hooks can run, so keep AntiStallCodex focused and fail open on uncertainty.

Known caveats from community/GitHub reports:

- Some Codex Desktop builds have had UI issues showing completed Stop hook details.
- Some releases have had continuation edge cases after a blocking Stop hook. Keep the anti-loop guard and block cap conservative.
- `PreToolUse` coverage is useful but incomplete; AntiStallCodex should rely on `Stop`, not tool-call interception.
