# Hermes Slack Watcher

Community Hermes skill plus optional helper tools for connecting [Hermes Agent](https://github.com/NousResearch/hermes-agent) to Slack as a private, user-gated channel watcher.

It lets Hermes:

- listen to selected Slack channels where the bot is invited;
- only obey one configured owner user;
- avoid public replies in monitored channels;
- send owner-only private Slack responses in the origin channel;
- copy answers to a private home channel so the conversation can continue;
- store monitored-channel history in local SQLite for summaries and search;
- work without requiring Mem0, Obsidian, vector DBs, or any specific memory provider.

## Install The Skill

Install through Hermes' standard skill installer:

```bash
hermes skills install gitlares/hermes-slack/skill/slack-hermes-watcher --yes
```

This installs the safe skill bundle only. Hermes community skill scanning blocks bundles that contain token-handling scripts or privileged restart commands, so automation helpers live outside the installed skill.

After installing, ask Hermes:

```text
Use slack-hermes-watcher to configure Slack supervision.
```

The skill will guide the full process: Slack App creation, owner user ID, private home channel, monitored channels, watcher tools, SQLite history, memory policy, validation, and troubleshooting.

## Optional Helper Tools

If you want guided automation after installing the skill, clone this repo and run the external helper:

```bash
git clone git@github.com:gitlares/hermes-slack.git
cd hermes-slack
python tools/setup_wizard.py
```

The helper generates a Slack manifest, asks for tokens locally, resolves user/channel names, configures Hermes, installs the companion plugin, applies supported runtime patches, validates imports, and offers to restart `hermes-gateway`.

The helper is intentionally outside the installed skill bundle because it handles secrets and local runtime changes.

## Repository Layout

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

## Companion Plugin Tools

The optional `slack_api` Hermes plugin exposes:

- `slack_list_channels`
- `slack_channel_history`
- `slack_search_messages`
- `slack_watcher_channels`
- `slack_watcher_recent`
- `slack_watcher_search`
- `slack_watcher_backfill`

## Security Notes

Never commit `.env`, Slack tokens, SQLite databases, or local Hermes configs.

The installed skill does not contain token-handling scripts. External helper tools operate locally and should be reviewed before use.
