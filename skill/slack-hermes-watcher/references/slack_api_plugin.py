"""Slack API and passive SQLite watcher tools for Hermes."""

from __future__ import annotations

import json
import os
import sqlite3
import time
import urllib.parse
import urllib.request
from typing import Any


def _env(name: str) -> str:
    value = os.environ.get(name, "")
    if value:
        return value
    path = os.path.expanduser("~/.hermes/.env")
    try:
        for line in open(path, encoding="utf-8"):
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def _api(method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    token = _env("SLACK_BOT_TOKEN")
    if not token:
        return {"ok": False, "error": "SLACK_BOT_TOKEN is not configured"}
    req = urllib.request.Request(
        "https://slack.com/api/" + method,
        data=urllib.parse.urlencode(payload or {}).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _fmt(ts: str) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(ts)))
    except Exception:
        return ts


def _clean(text: str, limit: int = 1600) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text[:limit] + ("..." if len(text) > limit else "")


def _db_path() -> str:
    return os.path.expanduser(_env("SLACK_WATCHER_DB_PATH") or "~/.hermes/slack_watcher.sqlite3")


def _watch_channels() -> list[str]:
    return [x.strip() for x in _env("SLACK_WATCH_CHANNELS").split(",") if x.strip()]


def _conn() -> sqlite3.Connection:
    path = _db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _schema(conn: sqlite3.Connection) -> None:
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


def _has_table(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='slack_messages'").fetchone() is not None


def _row(row: sqlite3.Row) -> dict[str, Any]:
    ts = str(row["ts"] or "")
    return {
        "channel_id": row["channel_id"],
        "channel_name": row["channel_name"] or row["channel_id"],
        "user_id": row["user_id"] or "",
        "user_name": row["user_name"] or row["user_id"] or "",
        "ts": ts,
        "time": _fmt(ts),
        "thread_ts": row["thread_ts"] or "",
        "text": _clean(row["text"] or "", 2200),
    }


def _types(pub: bool, priv: bool, dms: bool) -> str:
    out = []
    if pub:
        out.append("public_channel")
    if priv:
        out.append("private_channel")
    if dms:
        out.extend(["im", "mpim"])
    return ",".join(out) or "public_channel,private_channel"


def _list_channels(args: dict[str, Any], **_: Any) -> str:
    limit = max(1, min(int(args.get("limit") or 100), 500))
    only_joined = bool(args.get("only_joined", True))
    cursor = ""
    channels = []
    while True:
        res = _api("conversations.list", {
            "types": _types(bool(args.get("include_public", True)), bool(args.get("include_private", True)), bool(args.get("include_dms", False))),
            "exclude_archived": "true",
            "limit": min(limit, 200),
            **({"cursor": cursor} if cursor else {}),
        })
        if not res.get("ok"):
            return json.dumps(res, ensure_ascii=False)
        for ch in res.get("channels", []):
            if only_joined and not ch.get("is_member"):
                continue
            channels.append({"id": ch.get("id"), "name": ch.get("name") or ch.get("id"), "is_member": bool(ch.get("is_member")), "is_private": bool(ch.get("is_private"))})
            if len(channels) >= limit:
                return json.dumps({"ok": True, "channels": channels}, ensure_ascii=False)
        cursor = (res.get("response_metadata") or {}).get("next_cursor") or ""
        if not cursor:
            return json.dumps({"ok": True, "channels": channels}, ensure_ascii=False)


def _channel_history(args: dict[str, Any], **_: Any) -> str:
    channel = str(args.get("channel") or "").strip()
    if not channel:
        return json.dumps({"ok": False, "error": "channel is required"}, ensure_ascii=False)
    res = _api("conversations.history", {"channel": channel, "limit": max(1, min(int(args.get("limit") or 20), 100))})
    if not res.get("ok"):
        return json.dumps(res, ensure_ascii=False)
    messages = [{"ts": m.get("ts"), "time": _fmt(str(m.get("ts", ""))), "user": m.get("user") or m.get("bot_id") or "", "thread_ts": m.get("thread_ts", ""), "text": _clean(m.get("text", ""))} for m in res.get("messages", [])]
    return json.dumps({"ok": True, "channel": channel, "messages": messages}, ensure_ascii=False)


def _search_messages(args: dict[str, Any], **_: Any) -> str:
    query = str(args.get("query") or "").lower().strip()
    if not query:
        return json.dumps({"ok": False, "error": "query is required"}, ensure_ascii=False)
    channels = json.loads(_list_channels({"only_joined": True, "limit": 200})).get("channels", [])
    target = str(args.get("channel") or "").strip()
    if target:
        channels = [c for c in channels if c.get("id") == target or c.get("name") == target]
    limit = max(1, min(int(args.get("limit") or 50), 100))
    results = []
    for ch in channels:
        res = _api("conversations.history", {"channel": ch["id"], "limit": max(limit, 50)})
        if not res.get("ok"):
            continue
        for m in res.get("messages", []):
            if query in (m.get("text", "").lower()):
                results.append({"channel_id": ch["id"], "channel_name": ch.get("name"), "ts": m.get("ts"), "time": _fmt(str(m.get("ts", ""))), "user": m.get("user") or m.get("bot_id") or "", "text": _clean(m.get("text", ""))})
                if len(results) >= limit:
                    return json.dumps({"ok": True, "results": results}, ensure_ascii=False)
    return json.dumps({"ok": True, "results": results}, ensure_ascii=False)


def _watcher_channels(args: dict[str, Any], **_: Any) -> str:
    if not os.path.exists(_db_path()):
        return json.dumps({"ok": True, "configured_channels": _watch_channels(), "db_path": _db_path(), "channels": []}, ensure_ascii=False)
    with _conn() as conn:
        if not _has_table(conn):
            return json.dumps({"ok": True, "configured_channels": _watch_channels(), "db_path": _db_path(), "channels": []}, ensure_ascii=False)
        rows = conn.execute("SELECT channel_id, channel_name, COUNT(*) message_count, MAX(ts) last_ts FROM slack_messages GROUP BY channel_id, channel_name ORDER BY MAX(created_at) DESC").fetchall()
    channels = [{"channel_id": r["channel_id"], "channel_name": r["channel_name"] or r["channel_id"], "message_count": r["message_count"], "last_ts": r["last_ts"], "last_time": _fmt(str(r["last_ts"] or ""))} for r in rows]
    return json.dumps({"ok": True, "configured_channels": _watch_channels(), "db_path": _db_path(), "channels": channels}, ensure_ascii=False)


def _watcher_recent(args: dict[str, Any], **_: Any) -> str:
    channel = str(args.get("channel") or "").strip()
    since = time.time() - float(args.get("since_hours") or 24) * 3600
    limit = max(1, min(int(args.get("limit") or 50), 200))
    if not os.path.exists(_db_path()):
        return json.dumps({"ok": True, "messages": [], "db_path": _db_path()}, ensure_ascii=False)
    with _conn() as conn:
        if not _has_table(conn):
            return json.dumps({"ok": True, "messages": [], "db_path": _db_path()}, ensure_ascii=False)
        params: list[Any] = [since]
        where = "created_at >= ?"
        if channel:
            where += " AND (channel_id = ? OR channel_name = ?)"
            params += [channel, channel]
        rows = conn.execute(f"SELECT * FROM slack_messages WHERE {where} ORDER BY CAST(ts AS REAL) DESC LIMIT ?", params + [limit]).fetchall()
    return json.dumps({"ok": True, "messages": [_row(r) for r in reversed(rows)]}, ensure_ascii=False)


def _watcher_search(args: dict[str, Any], **_: Any) -> str:
    query = str(args.get("query") or "").strip()
    if not query:
        return json.dumps({"ok": False, "error": "query is required"}, ensure_ascii=False)
    channel = str(args.get("channel") or "").strip()
    since = time.time() - float(args.get("since_hours") or 168) * 3600
    limit = max(1, min(int(args.get("limit") or 50), 200))
    if not os.path.exists(_db_path()):
        return json.dumps({"ok": True, "results": [], "db_path": _db_path()}, ensure_ascii=False)
    with _conn() as conn:
        if not _has_table(conn):
            return json.dumps({"ok": True, "results": [], "db_path": _db_path()}, ensure_ascii=False)
        params: list[Any] = [since, f"%{query}%"]
        where = "created_at >= ? AND text LIKE ?"
        if channel:
            where += " AND (channel_id = ? OR channel_name = ?)"
            params += [channel, channel]
        rows = conn.execute(f"SELECT * FROM slack_messages WHERE {where} ORDER BY CAST(ts AS REAL) DESC LIMIT ?", params + [limit]).fetchall()
    return json.dumps({"ok": True, "results": [_row(r) for r in reversed(rows)]}, ensure_ascii=False)


def _watcher_backfill(args: dict[str, Any], **_: Any) -> str:
    channels = args.get("channels") or _watch_channels()
    if isinstance(channels, str):
        channels = [x.strip() for x in channels.split(",") if x.strip()]
    channels = [str(c).strip() for c in channels if str(c).strip() and str(c).strip() != "*"]
    if not channels:
        return json.dumps({"ok": False, "error": "No channels provided"}, ensure_ascii=False)
    limit = max(1, min(int(args.get("limit") or 100), 500))
    inserted = scanned = 0
    errors = []
    with _conn() as conn:
        _schema(conn)
        for channel in channels:
            res = _api("conversations.history", {"channel": channel, "limit": limit})
            if not res.get("ok"):
                errors.append({"channel": channel, "error": str(res.get("error") or res)})
                continue
            info = _api("conversations.info", {"channel": channel})
            name = ((info.get("channel") or {}).get("name") if info.get("ok") else "") or channel
            for msg in res.get("messages", []):
                if not args.get("include_bots", False) and (msg.get("bot_id") or msg.get("subtype") == "bot_message"):
                    continue
                ts = str(msg.get("ts") or "")
                if not ts:
                    continue
                scanned += 1
                cur = conn.execute("INSERT OR IGNORE INTO slack_messages (team_id, channel_id, channel_name, user_id, user_name, ts, thread_ts, text, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", ("", channel, name, msg.get("user") or msg.get("bot_id") or "", msg.get("user") or msg.get("bot_id") or "", ts, msg.get("thread_ts") or "", msg.get("text", ""), time.time()))
                inserted += int(cur.rowcount or 0)
    return json.dumps({"ok": True, "channels": channels, "scanned": scanned, "inserted": inserted, "errors": errors, "db_path": _db_path()}, ensure_ascii=False)


def _available() -> bool:
    return bool(_env("SLACK_BOT_TOKEN"))


def register(ctx) -> None:
    tools = [
        ("slack_list_channels", _list_channels, {"type": "object", "properties": {"include_public": {"type": "boolean", "default": True}, "include_private": {"type": "boolean", "default": True}, "include_dms": {"type": "boolean", "default": False}, "only_joined": {"type": "boolean", "default": True}, "limit": {"type": "integer", "default": 100}}}, "List Slack channels visible to Hermes."),
        ("slack_channel_history", _channel_history, {"type": "object", "properties": {"channel": {"type": "string"}, "limit": {"type": "integer", "default": 20}}, "required": ["channel"]}, "Read recent Slack messages from a channel."),
        ("slack_search_messages", _search_messages, {"type": "object", "properties": {"query": {"type": "string"}, "channel": {"type": "string"}, "limit": {"type": "integer", "default": 50}}, "required": ["query"]}, "Search recent Slack messages through Slack API."),
        ("slack_watcher_channels", _watcher_channels, {"type": "object", "properties": {}}, "List channels indexed by the local watcher."),
        ("slack_watcher_recent", _watcher_recent, {"type": "object", "properties": {"channel": {"type": "string"}, "since_hours": {"type": "number", "default": 24}, "limit": {"type": "integer", "default": 50}}}, "Read recent local watcher messages."),
        ("slack_watcher_search", _watcher_search, {"type": "object", "properties": {"query": {"type": "string"}, "channel": {"type": "string"}, "since_hours": {"type": "number", "default": 168}, "limit": {"type": "integer", "default": 50}}, "required": ["query"]}, "Search local watcher messages."),
        ("slack_watcher_backfill", _watcher_backfill, {"type": "object", "properties": {"channels": {"type": ["string", "array"]}, "limit": {"type": "integer", "default": 100}, "include_bots": {"type": "boolean", "default": False}}}, "Backfill recent Slack history into watcher SQLite."),
    ]
    for name, handler, schema, description in tools:
        ctx.register_tool(name=name, toolset="hermes-slack", schema=schema, handler=handler, check_fn=_available if "slack_watcher_" not in name or name == "slack_watcher_backfill" else (lambda: True), requires_env=["SLACK_BOT_TOKEN"] if name in {"slack_list_channels", "slack_channel_history", "slack_search_messages", "slack_watcher_backfill"} else [], description=description, emoji="💬")
