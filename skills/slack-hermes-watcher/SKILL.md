---
name: slack-hermes-watcher
description: Guide Hermes through configuring private, user-gated Slack channel supervision. Use when a user wants Hermes to listen to selected Slack channels, identify the owner's Slack user ID, choose a private home channel, configure monitored channels, install Slack watcher tools, store channel history in SQLite, and define memory rules without requiring Mem0 or any specific memory provider.
---

# Slack Hermes Watcher

## Goal

Help the user set up Hermes as a Slack listener that can supervise selected channels without speaking publicly.

Target behavior:

- Only the configured owner can activate Hermes.
- Normal conversation happens in a private home channel.
- Mentions in monitored channels produce a private owner-only Slack response and a copy in the home channel.
- Monitored channel history is stored locally in SQLite for summaries/searches.
- Long-term memory is optional and provider-agnostic.

## Installation Rule

This skill must be installed through Hermes' normal skill installer. Do not present root-level repo scripts as the primary installation path.

Canonical install identifier:

```bash
hermes skills install gitlares/hermes-slack/skills/slack-hermes-watcher --yes
```

Legacy path still works for older docs:

```bash
hermes skills install gitlares/hermes-slack/skill/slack-hermes-watcher --yes
```

After installation, guide the user through the setup. If they want automation, use the helper scripts from the public repository as optional external tooling, not as part of the installed skill bundle.

## Setup Workflow

1. Create the Slack App.
2. Enable Socket Mode.
3. Install the app to the Slack workspace.
4. Collect the Slack bot token and app token from the user without storing or displaying them unnecessarily.
5. Resolve the owner's Slack user ID.
6. Resolve the private Hermes home channel ID.
7. Resolve monitored channel IDs.
8. Configure Hermes Slack environment and channel policy.
9. Install or update the Slack watcher plugin.
10. Verify runtime behavior.
11. Backfill recent channel history.
12. Test summary/search requests.

## Slack App Requirements

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

Required events:

- `app_mention`
- `message.channels`
- `message.groups`
- `message.im`

Socket Mode requires an app-level token with:

- `connections:write`

Read `references/slack-app-setup.md` when the user needs Slack UI guidance.
Use `references/slack-manifest-template.md` when the user needs a manifest to paste into Slack.

## Configuration Values To Collect

Collect these values:

- Slack bot token.
- Slack app-level token.
- Owner Slack user ID.
- Private Hermes home channel ID.
- Monitored channel IDs.
- Local SQLite watcher database location.
- Retention policy for watcher rows, for example `SLACK_WATCH_RETENTION_DAYS=30`.

Use Slack API lookups or Slack UI instructions to help the user find IDs. Avoid hardcoding personal IDs in reusable documentation.

## Runtime Policy

Configure Hermes so Slack behaves as follows:

- In the home channel, reply normally.
- In monitored channels, listen and store messages passively.
- In monitored channels, never post public normal replies.
- If the owner mentions Hermes outside the home channel, respond privately in that channel and copy the full answer to the home channel.
- Ignore non-owner activation attempts.
- Keep other Hermes channels such as WebUI or WhatsApp unaffected.

## Watcher Tools

The companion Slack watcher plugin should expose:

- `slack_list_channels`
- `slack_channel_history`
- `slack_search_messages`
- `slack_watcher_channels`
- `slack_watcher_recent`
- `slack_watcher_search`
- `slack_watcher_backfill`
- `slack_watcher_prune`

Use watcher tools for monitored-channel summaries because they read SQLite history without filling the prompt context.

## Memory Policy

SQLite is the source of truth for monitored Slack history.

Do not keep unbounded history by default. Recommend a retention window such as 30 or 60 days and use a prune operation periodically.

Do not put every Slack message into long-term memory. Promote only durable facts when the owner asks to remember them or confirms an extracted item is important.

Accept any long-term memory system:

- Mem0.
- Obsidian or vault files.
- SQLite task tables.
- custom MCP memory.
- no long-term memory provider.

The Slack watcher must remain useful with SQLite alone.

## Validation

After setup:

1. Confirm Hermes can list Slack channels visible to the bot.
2. Confirm the home channel and monitored channels resolve to IDs.
3. Confirm the watcher database receives new messages from monitored channels.
4. Backfill recent history.
5. Ask for a summary of a monitored channel.
6. Mention Hermes from a monitored channel as the owner.
7. Confirm the origin channel receives only a private owner-visible response.
8. Confirm the private home channel receives the copied answer.
9. Confirm another Slack user cannot activate Hermes.

If Hermes says it cannot access Slack after tools are installed, verify tools are registered and clear stale Slack sessions that may contain old context.
