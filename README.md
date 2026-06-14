# Hermes Slack Watcher

Community skill and helper scripts for connecting [Hermes Agent](https://github.com/NousResearch/hermes-agent) to Slack as a private, user-gated channel watcher.

It lets Hermes:

- listen to selected Slack channels where the bot is invited;
- only obey one configured owner user;
- avoid public replies in monitored channels;
- send owner-only ephemeral responses in the origin channel;
- copy answers to a private home channel so the conversation can continue;
- store monitored-channel history in local SQLite for summaries and search;
- work without requiring Mem0, Obsidian, vector DBs, or any specific memory provider.

## Repository Layout

```text
setup via Hermes:
  hermes skills install gitlares/hermes-slack/skill/slack-hermes-watcher --yes

skill/slack-hermes-watcher/
  SKILL.md
  scripts/
    setup_wizard.py
    slack_manifest.py
    configure_env.py
    install_plugin.py
    patch_runtime.py
  references/
    slack_api_plugin.py
    slack_api_plugin.yaml
    slack-app-setup.md
    hermes-runtime-behavior.md
```

## Install The Skill

Install through Hermes' standard skill installer:

```bash
hermes skills install gitlares/hermes-slack/skill/slack-hermes-watcher --yes
```

Then run the guided setup script from the installed skill directory:

```bash
python ~/.hermes/skills/slack-hermes-watcher/scripts/setup_wizard.py
```

If you installed into a category, adjust the path, for example:

```bash
python ~/.hermes/skills/community/slack-hermes-watcher/scripts/setup_wizard.py
```

The wizard generates a Slack manifest, waits for you to create/install the Slack app, asks for the Slack tokens, resolves your owner user ID and channels, configures Hermes, installs the watcher plugin, applies supported runtime patches, and offers to restart `hermes-gateway`.

If you prefer manual setup, use the steps below.

## Manual Setup

Clone this repository only if you want to inspect or modify the source:

```bash
git clone git@github.com:gitlares/hermes-slack.git
cd hermes-slack
```

Generate a Slack manifest:

```bash
python skill/slack-hermes-watcher/scripts/slack_manifest.py --name Hermes > slack-manifest.json
```

Create a Slack App from that manifest, enable Socket Mode, install the app, and collect:

- `SLACK_BOT_TOKEN` (`xoxb-...`)
- `SLACK_APP_TOKEN` (`xapp-...`)

Configure Hermes:

```bash
python skill/slack-hermes-watcher/scripts/configure_env.py \
  --env ~/.hermes/.env \
  --bot-token "$SLACK_BOT_TOKEN" \
  --app-token "$SLACK_APP_TOKEN" \
  --owner "@Your Name" \
  --home "#your-private-hermes-channel" \
  --watch "#channel-a,#channel-b"
```

Install the Hermes plugin:

```bash
python skill/slack-hermes-watcher/scripts/install_plugin.py \
  --hermes-root ~/.hermes/hermes-agent
```

Patch supported Hermes runtime layouts:

```bash
python skill/slack-hermes-watcher/scripts/patch_runtime.py \
  --hermes-root ~/.hermes/hermes-agent
```

Restart Hermes:

```bash
sudo systemctl restart hermes-gateway
```

Backfill recent Slack history:

```text
Ask Hermes to run slack_watcher_backfill for the configured channels.
```

## What The Installer Configures

The installer writes these local Hermes environment values:

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

It does not commit, upload, or transmit tokens anywhere except Slack API calls needed to resolve user/channel names.

## Slack App Requirements

Bot scopes:

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

Events:

- `app_mention`
- `message.channels`
- `message.groups`
- `message.im`

App-level token scope:

- `connections:write`

## Watcher Tools

The bundled Hermes plugin exposes:

- `slack_list_channels`
- `slack_channel_history`
- `slack_search_messages`
- `slack_watcher_channels`
- `slack_watcher_recent`
- `slack_watcher_search`
- `slack_watcher_backfill`

## Memory Model

The watcher stores Slack history in SQLite. It does not require a long-term memory provider.

Use long-term memory only for durable facts the owner explicitly wants to remember.

## Security Notes

Never commit `.env`, Slack tokens, SQLite databases, or local Hermes configs.

This project is designed around owner-only activation. Review generated config before running it on a shared workspace.
