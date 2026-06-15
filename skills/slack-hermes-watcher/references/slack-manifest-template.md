# Slack Manifest Template

Use this manifest as a starting point when creating the Slack App from the Slack UI.

```json
{
  "_metadata": {
    "major_version": 1,
    "minor_version": 1
  },
  "display_information": {
    "name": "Hermes",
    "description": "Private Hermes assistant and Slack channel watcher",
    "background_color": "#1a1a2e"
  },
  "features": {
    "bot_user": {
      "display_name": "Hermes",
      "always_online": true
    },
    "slash_commands": [
      {
        "command": "/hermes",
        "description": "Control Hermes",
        "usage_hint": "sethome | help",
        "should_escape": false
      }
    ]
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
        "users:read"
      ]
    }
  },
  "settings": {
    "event_subscriptions": {
      "bot_events": [
        "app_mention",
        "message.channels",
        "message.groups",
        "message.im"
      ]
    },
    "interactivity": {
      "is_enabled": true
    },
    "org_deploy_enabled": false,
    "socket_mode_enabled": true,
    "token_rotation_enabled": false
  }
}
```
