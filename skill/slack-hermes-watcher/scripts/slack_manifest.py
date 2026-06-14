#!/usr/bin/env python3
"""Generate a Slack manifest for a Hermes watcher app."""

from __future__ import annotations

import argparse
import json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="Hermes")
    parser.add_argument("--description", default="Private Hermes assistant and Slack channel watcher")
    args = parser.parse_args()

    manifest = {
        "_metadata": {"major_version": 1, "minor_version": 1},
        "display_information": {
            "name": args.name,
            "description": args.description,
            "background_color": "#1a1a2e",
        },
        "features": {
            "bot_user": {
                "display_name": args.name,
                "always_online": True,
            },
            "slash_commands": [
                {
                    "command": "/hermes",
                    "description": "Control Hermes",
                    "usage_hint": "sethome | help",
                    "should_escape": False,
                }
            ],
        },
        "oauth_config": {
            "scopes": {
                "bot": [
                    "app_mentions:read",
                    "assistant:write",
                    "channels:history",
                    "channels:read",
                    "chat:write",
                    "commands",
                    "files:read",
                    "files:write",
                    "groups:history",
                    "groups:read",
                    "im:history",
                    "im:read",
                    "im:write",
                    "users:read",
                ]
            }
        },
        "settings": {
            "event_subscriptions": {
                "bot_events": [
                    "app_mention",
                    "message.channels",
                    "message.groups",
                    "message.im",
                ]
            },
            "interactivity": {"is_enabled": True},
            "org_deploy_enabled": False,
            "socket_mode_enabled": True,
            "token_rotation_enabled": False,
        },
    }
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
