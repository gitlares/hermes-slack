# Hermes Runtime Behavior

Use this before editing Hermes internals. Hermes source changes across versions, so inspect before patching.

## Required Behavior

- Owner-only activation: enforce `SLACK_ALLOWED_USERS`.
- Home channel normal replies: `SLACK_HOME_CHANNEL`.
- Monitored channels passive capture: store messages in SQLite.
- Outside home, owner mentions should produce:
  - an ephemeral Slack response in the origin channel visible only to owner;
  - a copied answer in home channel for continued conversation.
- Other users should be ignored.
- Public replies in monitored channels should not happen.

## Environment Contract

```bash
SLACK_ALLOWED_USERS=U...
SLACK_HOME_CHANNEL=C...
SLACK_HOME_CHANNEL_NAME=asistente-hermes
SLACK_FREE_RESPONSE_CHANNELS=C...
SLACK_REQUIRE_MENTION=true
SLACK_STRICT_MENTION=false
SLACK_ALLOW_BOTS=false
SLACK_WATCH_CHANNELS=C...,G...
SLACK_WATCHER_DB_PATH=~/.hermes/slack_watcher.sqlite3
```

## Adapter Patch Points

In `gateway/platforms/slack.py`, inspect:

- Slack `send(...)`: route non-home responses to ephemeral + home copy.
- Slack inbound message handler: after extracting `channel_id`, `user_id`, `text`, `ts`, store watched channel messages in SQLite before mention gating returns.
- Existing `send_private_notice(...)`: use as a model for `chat_postEphemeral`.

Do not remove `terminal`, `mcp`, or other Hermes tools from Slack as a shortcut. Security should be enforced by allowed user/channel routing, not by degrading Slack toolsets.

## Session Hygiene

If Hermes keeps saying it cannot access Slack after tools are installed:

1. Verify `slack_*` tools are registered.
2. Clear stale Slack sessions from Hermes session storage.
3. Restart `hermes-gateway`.

Old Slack sessions can carry prompt history like “I cannot read channels” even after tools are added.

## SQLite Policy

Store raw channel messages in SQLite only. Do not auto-promote every message to long-term memory.

Use long-term memory only when:

- the owner says “remember this”;
- the owner confirms a proposed durable fact;
- a workflow explicitly extracts decisions/tasks and asks to save them.
