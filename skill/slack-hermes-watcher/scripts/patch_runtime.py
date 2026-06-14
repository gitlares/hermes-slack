#!/usr/bin/env python3
"""Best-effort Hermes Slack runtime patcher for watcher behavior.

This patches known Hermes source shapes. If a pattern is missing, it fails
without writing partial changes.
"""

from __future__ import annotations

import argparse
from pathlib import Path


HELPERS = r'''
    def _slack_watcher_db_path(self) -> str:
        raw = (
            self.config.extra.get("watcher_db_path")
            or os.getenv("SLACK_WATCHER_DB_PATH")
            or "~/.hermes/slack_watcher.sqlite3"
        )
        return os.path.expanduser(str(raw))

    def _slack_watcher_channels(self) -> set:
        raw = self.config.extra.get("watch_channels")
        if raw is None:
            raw = os.getenv("SLACK_WATCH_CHANNELS", "")
        if isinstance(raw, (list, tuple, set)):
            values = raw
        else:
            values = str(raw or "").split(",")
        return {str(value).strip() for value in values if str(value).strip()}

    def _slack_watcher_enabled_for(self, channel_id: str, channel_name: str = "") -> bool:
        watched = self._slack_watcher_channels()
        if not watched:
            return False
        return "*" in watched or channel_id in watched or channel_name in watched

    async def _slack_channel_name(self, channel_id: str, team_id: str = "") -> str:
        if not channel_id:
            return ""
        cached = self._channel_name_cache.get(channel_id)
        if cached:
            return cached
        try:
            result = await self._get_client(channel_id).conversations_info(channel=channel_id)
            if result.get("ok"):
                channel = result.get("channel") or {}
                name = channel.get("name") or channel.get("user") or channel_id
                self._channel_name_cache[channel_id] = name
                return name
        except Exception as exc:
            logger.debug("[Slack] watcher channel name lookup failed for %s: %s", channel_id, exc)
        return channel_id

    def _store_slack_watcher_message(
        self,
        *,
        channel_id: str,
        channel_name: str,
        user_id: str,
        user_name: str,
        ts: str,
        thread_ts: str,
        text: str,
        team_id: str,
    ) -> None:
        if not channel_id or not ts:
            return
        db_path = self._slack_watcher_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with sqlite3.connect(db_path, timeout=5) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS slack_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id TEXT,
                    channel_id TEXT NOT NULL,
                    channel_name TEXT,
                    user_id TEXT,
                    user_name TEXT,
                    ts TEXT NOT NULL,
                    thread_ts TEXT,
                    text TEXT,
                    created_at REAL NOT NULL,
                    UNIQUE(channel_id, ts)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_slack_messages_channel_ts ON slack_messages(channel_id, ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_slack_messages_created ON slack_messages(created_at)")
            conn.execute(
                """
                INSERT OR IGNORE INTO slack_messages
                (team_id, channel_id, channel_name, user_id, user_name, ts, thread_ts, text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (team_id, channel_id, channel_name, user_id, user_name, ts, thread_ts, text, time.time()),
            )
'''


STORE_BLOCK = r'''
        watcher_channel_name = ""
        if not is_dm:
            watcher_channel_name = await self._slack_channel_name(channel_id, team_id)
            if self._slack_watcher_enabled_for(channel_id, watcher_channel_name):
                try:
                    watcher_user_name = await self._resolve_user_name(user_id, chat_id=channel_id)
                    self._store_slack_watcher_message(
                        channel_id=channel_id,
                        channel_name=watcher_channel_name,
                        user_id=user_id,
                        user_name=watcher_user_name,
                        ts=ts,
                        thread_ts=event.get("thread_ts") or "",
                        text=text,
                        team_id=team_id,
                    )
                except Exception as exc:
                    logger.warning("[Slack] watcher failed to store message in %s: %s", channel_id, exc)
'''


EPHEMERAL_BLOCK = r'''
            home = getattr(self.config, "home_channel", None)
            home_chat_id = getattr(home, "chat_id", None) if home else None
            if home_chat_id and chat_id and chat_id != home_chat_id:
                origin_chat_id = chat_id
                allowed_users = [
                    user.strip()
                    for user in os.getenv("SLACK_ALLOWED_USERS", "").split(",")
                    if user.strip() and user.strip() != "*"
                ]
                ephemeral_user = (
                    os.getenv("SLACK_EPHEMERAL_USER_ID", "").strip()
                    or (allowed_users[0] if allowed_users else "")
                )
                if ephemeral_user:
                    note = (
                        "_Solo tú puedes ver esta respuesta. "
                        f"Para conversar conmigo, escríbeme en <#{home_chat_id}>._\n\n"
                    )
                    formatted = self.format_message(note + content)
                    chunks = self.truncate_message(formatted, self.MAX_MESSAGE_LENGTH)
                    for chunk in chunks:
                        await self._get_client(chat_id).chat_postEphemeral(
                            channel=chat_id,
                            user=ephemeral_user,
                            text=chunk,
                            mrkdwn=True,
                        )
                chat_id = home_chat_id
                reply_to = None
                metadata = None
                content = f"_Continuación desde <#{origin_chat_id}>._\n\n{content}"
'''


SESSION_NOTE = (
    "slack_search_messages, slack_watcher_channels, slack_watcher_recent, "
    "and slack_watcher_search. Use watcher tools for monitored-channel "
    "summaries and searches because they read the local SQLite watcher "
    "history without filling the prompt context. These tools are read-only. Do not claim "
)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Could not find patch point: {label}")
    return text.replace(old, new, 1)


def patch_slack(path: Path) -> str:
    text = path.read_text()
    original = text
    if "import sqlite3" not in text:
        text = replace_once(text, "import re\n", "import re\nimport sqlite3\n", "sqlite3 import")
    if "self._channel_name_cache" not in text:
        text = replace_once(
            text,
            "        self._channel_team: Dict[str, str] = {}  # channel_id → team_id\n",
            "        self._channel_team: Dict[str, str] = {}  # channel_id → team_id\n"
            "        self._channel_name_cache: Dict[str, str] = {}  # channel_id → channel name\n",
            "channel name cache",
        )
    if "_slack_watcher_db_path" not in text:
        text = replace_once(text, "    def _start_socket_mode_handler(self) -> None:\n", HELPERS + "\n    def _start_socket_mode_handler(self) -> None:\n", "watcher helper methods")
    if "_store_slack_watcher_message(" not in text.split("        # Build thread_ts for session keying.", 1)[0]:
        text = replace_once(text, "        # Build thread_ts for session keying.\n", STORE_BLOCK + "\n        # Build thread_ts for session keying.\n", "passive message store")
    if "chat_postEphemeral" not in text.split("            # Convert standard markdown", 1)[0]:
        text = replace_once(text, "            # Convert standard markdown → Slack mrkdwn\n", EPHEMERAL_BLOCK + "\n            # Convert standard markdown → Slack mrkdwn\n", "ephemeral routing")
    if text != original:
        path.with_suffix(path.suffix + ".bak").write_text(original)
        path.write_text(text)
    return "patched" if text != original else "already patched"


def patch_session(path: Path) -> str:
    text = path.read_text()
    original = text
    old = "and slack_search_messages. These tools are read-only. Do not claim "
    if old in text and "slack_watcher_recent" not in text:
        text = text.replace(old, SESSION_NOTE, 1)
    if text != original:
        path.with_suffix(path.suffix + ".bak").write_text(original)
        path.write_text(text)
    return "patched" if text != original else "already patched"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-root", default="~/.hermes/hermes-agent")
    args = parser.parse_args()
    root = Path(args.hermes_root).expanduser()
    slack = root / "gateway" / "platforms" / "slack.py"
    session = root / "gateway" / "session.py"
    if not slack.exists() or not session.exists():
        raise SystemExit(f"Hermes source not found under {root}")
    print(f"slack.py: {patch_slack(slack)}")
    print(f"session.py: {patch_session(session)}")


if __name__ == "__main__":
    main()
