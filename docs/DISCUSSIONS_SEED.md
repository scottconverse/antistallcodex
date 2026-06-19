# Discussion Seed

## What AntiStallCodex solves

Codex can stop after a polished progress summary even when approved work remains. AntiStallCodex turns "do not stop early" from a reminder into a Codex Stop-hook continuation gate.

The user-facing commands are deliberately simple:

- `AntistallON: <goal>`
- `AntistallOFF`

## Why this is Codex-specific

AntiStallClaude uses Claude Code's Stop hook. AntiStallCodex uses Codex's Stop hook, where `decision: "block"` creates a continuation prompt. The state machine is similar, but the hook payload and installation target are Codex-native.

## Feedback wanted

- Does the Desktop app reliably load global hooks across projects?
- Does `/hooks` trust review feel clear enough for non-CLI users?
- Should `AntistallON` automatically set a Codex `/goal` too, or stay focused on Stop-hook enforcement?
