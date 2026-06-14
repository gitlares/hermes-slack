#!/usr/bin/env python3
"""Configure Hermes Slack watcher environment variables."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def slack_api(token: str, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = urllib.parse.urlencode(payload or {}).encode()
    req = urllib.request.Request(
        "https://slack.com/api/" + method,
        data=data,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode())


def channel_types() -> str:
    return "public_channel,private_channel,im,mpim"


def resolve_channel(token: str, value: str) -> tuple[str, str]:
    value = value.strip()
    if not value:
        return "", ""
    if re.match(r"^[CDG][A-Z0-9]+$", value):
        return value, value
    name = value.lstrip("#")
    cursor = ""
    while True:
        payload = {"types": channel_types(), "exclude_archived": "true", "limit": 200}
        if cursor:
            payload["cursor"] = cursor
        data = slack_api(token, "conversations.list", payload)
        if not data.get("ok"):
            raise RuntimeError(f"conversations.list failed: {data}")
        for ch in data.get("channels", []):
            if ch.get("name") == name or ch.get("id") == value:
                return ch["id"], ch.get("name") or ch["id"]
        cursor = (data.get("response_metadata") or {}).get("next_cursor") or ""
        if not cursor:
            break
    raise RuntimeError(f"Could not resolve Slack channel: {value}")


def resolve_user(token: str, value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if re.match(r"^U[A-Z0-9]+$", value):
        return value
    wanted = value.lstrip("@").lower()
    cursor = ""
    while True:
        payload = {"limit": 200}
        if cursor:
            payload["cursor"] = cursor
        data = slack_api(token, "users.list", payload)
        if not data.get("ok"):
            raise RuntimeError(f"users.list failed: {data}")
        for user in data.get("members", []):
            profile = user.get("profile") or {}
            candidates = {
                str(user.get("name") or "").lower(),
                str(user.get("real_name") or "").lower(),
                str(profile.get("display_name") or "").lower(),
                str(profile.get("real_name") or "").lower(),
            }
            if wanted in candidates:
                return user["id"]
        cursor = (data.get("response_metadata") or {}).get("next_cursor") or ""
        if not cursor:
            break
    raise RuntimeError(f"Could not resolve Slack user: {value}")


def update_env(path: Path, values: dict[str, str]) -> None:
    lines = path.read_text().splitlines() if path.exists() else []
    for key, value in values.items():
        replaced = False
        for i, line in enumerate(lines):
            if line.startswith(key + "="):
                lines[i] = f"{key}={value}"
                replaced = True
                break
        if not replaced:
            lines.append(f"{key}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default="~/.hermes/.env")
    parser.add_argument("--bot-token", default=os.getenv("SLACK_BOT_TOKEN", ""))
    parser.add_argument("--app-token", default=os.getenv("SLACK_APP_TOKEN", ""))
    parser.add_argument("--owner", required=True, help="Slack user ID or @name")
    parser.add_argument("--home", required=True, help="Slack channel ID or #name")
    parser.add_argument("--watch", default="", help="Comma-separated channel IDs or #names")
    parser.add_argument("--db-path", default="~/.hermes/slack_watcher.sqlite3")
    args = parser.parse_args()

    if not args.bot_token:
        raise SystemExit("SLACK bot token is required via --bot-token or SLACK_BOT_TOKEN")

    owner_id = resolve_user(args.bot_token, args.owner)
    home_id, home_name = resolve_channel(args.bot_token, args.home)
    watch_ids = []
    for item in [x.strip() for x in args.watch.split(",") if x.strip()]:
        channel_id, _ = resolve_channel(args.bot_token, item)
        watch_ids.append(channel_id)

    values = {
        "SLACK_BOT_TOKEN": args.bot_token,
        "SLACK_APP_TOKEN": args.app_token,
        "SLACK_ALLOWED_USERS": owner_id,
        "GATEWAY_ALLOW_ALL_USERS": "false",
        "SLACK_HOME_CHANNEL": home_id,
        "SLACK_HOME_CHANNEL_NAME": home_name,
        "SLACK_FREE_RESPONSE_CHANNELS": home_id,
        "SLACK_REQUIRE_MENTION": "true",
        "SLACK_STRICT_MENTION": "false",
        "SLACK_ALLOW_BOTS": "false",
        "SLACK_ALLOWED_CHANNELS": "",
        "SLACK_WATCH_CHANNELS": ",".join(watch_ids),
        "SLACK_WATCHER_DB_PATH": os.path.expanduser(args.db_path),
    }
    update_env(Path(os.path.expanduser(args.env)), values)
    print(json.dumps({"ok": True, "owner_id": owner_id, "home_channel": home_id, "watch_channels": watch_ids}, indent=2))


if __name__ == "__main__":
    main()
