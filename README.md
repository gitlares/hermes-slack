# Hermes Slack Watcher

A small toolkit for using [Hermes Agent](https://github.com/NousResearch/hermes-agent) as a private Slack watcher under one owner's control.

It is meant for a simple setup: Hermes can follow selected channels, keep history in SQLite, and answer only the person who owns the installation.

What it does:

- listen to selected Slack channels where the bot is invited;
- only obey one configured owner user;
- avoid public replies in monitored channels;
- send owner-only private Slack responses in the origin channel;
- copy answers to a private home channel so the conversation can continue;
- store monitored-channel history in local SQLite for summaries and search;
- work without requiring Mem0, Obsidian, vector DBs, or any specific memory provider.

## Install

Install through Hermes' standard skill installer:

```bash
hermes skills install gitlares/hermes-slack/skill/slack-hermes-watcher --yes
```

This installs only the safe skill bundle. Hermes blocks community skills that handle secrets or local runtime changes, so the setup helpers stay outside the installed skill.

After installing, ask Hermes:

```text
Use slack-hermes-watcher to configure Slack supervision.
```

The skill walks through the setup: Slack app, owner user ID, private home channel, monitored channels, watcher tools, SQLite history, memory policy, validation, and troubleshooting.

## Optional helper tools

If you want a guided local setup after installing the skill, clone this repo and run the helper:

```bash
git clone git@github.com:gitlares/hermes-slack.git
cd hermes-slack
python tools/setup_wizard.py
```

The helper generates a Slack manifest, asks for tokens locally, resolves user and channel names, configures Hermes, installs the companion plugin, applies the supported runtime patches, validates imports, and offers to restart `hermes-gateway`.

It stays outside the installed skill bundle because it touches secrets and local runtime state.

## Layout

```text
skill/slack-hermes-watcher/
  SKILL.md
  references/
    slack-app-setup.md
    slack-manifest-template.md

plugin/slack_api/
  __init__.py
  plugin.yaml

tools/
  setup_wizard.py
  slack_manifest.py
  configure_env.py
  install_plugin.py
  patch_runtime.py

docs/
  hermes-runtime-behavior.md
```

## Companion plugin tools

The optional `slack_api` Hermes plugin exposes:

- `slack_list_channels`
- `slack_channel_history`
- `slack_search_messages`
- `slack_watcher_channels`
- `slack_watcher_recent`
- `slack_watcher_search`
- `slack_watcher_backfill`
- `slack_watcher_prune`

## Retention

The watcher stores Slack history in SQLite, so prompt context stays clean, but the local database can still grow over time.

Use `SLACK_WATCH_RETENTION_DAYS` to define default retention, for example:

```bash
SLACK_WATCH_RETENTION_DAYS=30
```

Use `slack_watcher_prune` to clean old rows and optionally cap rows per channel.

## Security notes

Never commit `.env`, Slack tokens, SQLite databases, or local Hermes configs.

The installed skill does not contain token-handling scripts. External helper tools operate locally and should be reviewed before use.
