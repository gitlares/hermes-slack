---
name: slack-hermes-watcher
description: Configure a Slack app and Hermes integration for private, user-gated Slack supervision. Use when setting up Hermes to listen to invited Slack channels, identify the owner's Slack user ID, configure a private home channel, store monitored-channel history in SQLite, expose watcher search/summary tools, or package this workflow for reusable/community installation without requiring Mem0 or any specific memory provider.
---

# Slack Hermes Watcher

## Goal

Set up Hermes as a Slack listener that can supervise selected channels without speaking publicly:

- Only the configured owner can activate Hermes.
- Normal conversation happens in a private home channel.
- Mentions in monitored channels produce an ephemeral response visible only to the owner, plus a copy in the home channel.
- Passive channel history is stored in local SQLite for later summaries/searches.
- Long-term memory is optional; do not require Mem0, Obsidian, vector DBs, or any provider-specific memory.

## Workflow

Install this skill through Hermes first:

```bash
hermes skills install gitlares/hermes-slack/skill/slack-hermes-watcher --yes
```

After the skill is installed, prefer the bundled guided setup:

```bash
python ~/.hermes/skills/slack-hermes-watcher/scripts/setup_wizard.py
```

Use the manual workflow below when installing from the skill folder only, patching an existing deployment, or debugging.

1. Create or update the Slack App.
2. Install the app to the workspace and collect tokens.
3. Resolve owner `user_id`, home channel ID, and monitored channel IDs.
4. Configure Hermes `.env` and `config.yaml`.
5. Install the `slack_api` watcher tools plugin.
6. Patch or verify Hermes Slack adapter behavior for passive SQLite capture and private Slack delivery.
7. Backfill recent channel history and test.

## Slack App Setup

Use `scripts/slack_manifest.py` to generate a Slack manifest:

```bash
python scripts/slack_manifest.py --name Hermes
```

Read `references/slack-app-setup.md` when the user needs step-by-step Slack UI guidance.

Required bot scopes:

- `app_mentions:read`
- `assistant:write`
- `channels:history`
- `channels:read`
- `chat:write`
- `commands`
- `files:read`
- `files:write`
- `groups:history`
- `groups:read`
- `im:history`
- `im:read`
- `im:write`
- `users:read`

Required bot events:

- `app_mention`
- `message.channels`
- `message.groups`
- `message.im`

Socket Mode must be enabled and an app-level token with `connections:write` is required.

## Configuration

Use `scripts/configure_env.py` to update Hermes `.env` safely:

```bash
python scripts/configure_env.py \
  --env ~/.hermes/.env \
  --bot-token "$SLACK_BOT_TOKEN" \
  --app-token "$SLACK_APP_TOKEN" \
  --owner "@Your Name" \
  --home "#your-private-hermes-channel" \
  --watch "#channel-a,#channel-b"
```

The script resolves Slack names to IDs when given a bot token. It writes:

- `SLACK_BOT_TOKEN`
- `SLACK_APP_TOKEN`
- `SLACK_ALLOWED_USERS`
- `SLACK_HOME_CHANNEL`
- `SLACK_HOME_CHANNEL_NAME`
- `SLACK_FREE_RESPONSE_CHANNELS`
- `SLACK_REQUIRE_MENTION=true`
- `SLACK_STRICT_MENTION=false`
- `SLACK_ALLOW_BOTS=false`
- `SLACK_WATCH_CHANNELS`
- `SLACK_WATCHER_DB_PATH`

If names cannot be resolved, ask the user to provide raw IDs.

## Watcher Tools

Install the bundled watcher plugin:

```bash
python scripts/install_plugin.py --hermes-root ~/.hermes/hermes-agent
```

This installs a Hermes plugin with tools:

- `slack_list_channels`
- `slack_channel_history`
- `slack_search_messages`
- `slack_watcher_channels`
- `slack_watcher_recent`
- `slack_watcher_search`
- `slack_watcher_backfill`

Use `slack_watcher_recent` and `slack_watcher_search` for monitored-channel summaries. Use `slack_channel_history` only for direct Slack API reads when the local SQLite watcher does not have enough history.

## Runtime Behavior

Configure the gateway so Slack works this way:

- In the home channel: respond normally.
- In monitored channels: listen and store messages passively.
- If owner mentions Hermes outside home: send an ephemeral response in that channel and copy the full answer to home.
- If anyone other than owner mentions Hermes: ignore.
- Do not post public replies in monitored channels.

Read `references/hermes-runtime-behavior.md` before patching Hermes internals. Hermes versions differ, so inspect current files before applying patches.

For known Hermes source layouts, use the bundled best-effort patcher:

```bash
python scripts/patch_runtime.py --hermes-root ~/.hermes/hermes-agent
```

Then validate imports and restart:

```bash
cd ~/.hermes/hermes-agent
PYTHONDONTWRITEBYTECODE=1 venv/bin/python - <<'PY'
import gateway.platforms.slack
import gateway.session
print("ok")
PY
sudo systemctl restart hermes-gateway
```

## Memory Policy

SQLite is the source of truth for monitored Slack history.

Do not put every Slack message into long-term memory. Promote only durable facts when the owner asks to remember them or when the owner confirms an extracted item is important.

Accept any long-term memory system:

- Mem0
- Obsidian/vault files
- SQLite task tables
- custom MCP memory
- no memory provider

The watcher must remain useful with SQLite alone.

## Validation

After setup:

1. Run `slack_list_channels` and confirm the home and monitored channels are visible.
2. Run `slack_watcher_backfill` for configured channels.
3. Run `slack_watcher_channels` and verify message counts.
4. Mention Hermes from a monitored channel as the owner.
5. Confirm the monitored channel gets only an ephemeral response.
6. Confirm the private home channel receives the copied answer.
7. Ask from home: “resúmeme lo importante de #canal hoy”.

If Hermes says it cannot access Slack, verify the watcher tools are registered and clear old Slack sessions that may contain stale context.
