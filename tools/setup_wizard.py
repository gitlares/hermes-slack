#!/usr/bin/env python3
"""Interactive installer for Hermes Slack Watcher."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def redact_cmd(cmd: list[str]) -> list[str]:
    redacted = []
    redact_next = False
    for part in cmd:
        if redact_next:
            redacted.append("***")
            redact_next = False
            continue
        redacted.append(part)
        if part in {"--bot-token", "--app-token"}:
            redact_next = True
    return redacted


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(redact_cmd(cmd)))
    return subprocess.run(cmd, text=True, check=check)


def prompt(label: str, default: str = "", secret: bool = False) -> str:
    import getpass

    suffix = f" [{default}]" if default else ""
    if secret:
        value = getpass.getpass(f"{label}{suffix}: ").strip()
    else:
        value = input(f"{label}{suffix}: ").strip()
    return value or default


def yes(label: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    value = input(f"{label} [{d}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "s", "si", "sí"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Install and configure Hermes Slack Watcher.")
    parser.add_argument("--hermes-root", default="~/.hermes/hermes-agent")
    parser.add_argument("--env", default="~/.hermes/.env")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--bot-token", default=os.getenv("SLACK_BOT_TOKEN", ""))
    parser.add_argument("--app-token", default=os.getenv("SLACK_APP_TOKEN", ""))
    parser.add_argument("--owner", default="")
    parser.add_argument("--home", default="")
    parser.add_argument("--watch", default="")
    parser.add_argument("--skip-runtime-patch", action="store_true")
    parser.add_argument("--skip-restart", action="store_true")
    args = parser.parse_args()

    hermes_root = Path(args.hermes_root).expanduser()
    env_path = Path(args.env).expanduser()
    if not hermes_root.exists():
        raise SystemExit(f"Hermes root not found: {hermes_root}")

    print("Hermes Slack Watcher setup")
    print("==========================")
    print("This installer does not send or store tokens anywhere except your local Hermes .env file.")
    print()

    manifest_path = Path.cwd() / "slack-manifest.generated.json"
    manifest = subprocess.check_output(
        [sys.executable, str(TOOLS / "slack_manifest.py"), "--name", "Hermes"],
        text=True,
    )
    manifest_path.write_text(manifest)
    print(f"\nGenerated Slack manifest: {manifest_path}")
    print("Create/install the Slack app from this manifest before continuing.")
    print("Required tokens: SLACK_BOT_TOKEN (xoxb-...) and SLACK_APP_TOKEN (xapp-...).")

    if not args.non_interactive and not yes("Continue after creating/installing the Slack app?", True):
        print("Stop here. Re-run setup_wizard.py after creating the Slack app.")
        return

    bot_token = args.bot_token
    app_token = args.app_token
    owner = args.owner
    home = args.home
    watch = args.watch
    if not args.non_interactive:
        bot_token = bot_token or prompt("Slack Bot Token (xoxb-...)", secret=True)
        app_token = app_token or prompt("Slack App Token (xapp-...)", secret=True)
        owner = owner or prompt("Owner Slack user (@name or U...)", "")
        home = home or prompt("Private Hermes home channel (#name or C...)", "")
        watch = watch or prompt("Channels to monitor, comma-separated (#a,#b or C...,G...)", "")

    missing = [name for name, value in {
        "--bot-token": bot_token,
        "--app-token": app_token,
        "--owner": owner,
        "--home": home,
    }.items() if not value]
    if missing:
        raise SystemExit("Missing required values: " + ", ".join(missing))

    run([
        sys.executable,
        str(TOOLS / "configure_env.py"),
        "--env",
        str(env_path),
        "--bot-token",
        bot_token,
        "--app-token",
        app_token,
        "--owner",
        owner,
        "--home",
        home,
        "--watch",
        watch,
    ])

    run([
        sys.executable,
        str(TOOLS / "install_plugin.py"),
        "--hermes-root",
        str(hermes_root),
    ])

    if not args.skip_runtime_patch:
        run([
            sys.executable,
            str(TOOLS / "patch_runtime.py"),
            "--hermes-root",
            str(hermes_root),
        ])

    py = hermes_root / "venv" / "bin" / "python"
    if py.exists():
        run([
            str(py),
            "-c",
            "import gateway.platforms.slack; import gateway.session; print('Hermes imports OK')",
        ])

    hermes = hermes_root / "venv" / "bin" / "hermes"
    if hermes.exists():
        run([str(hermes), "plugins", "enable", "slack-api"], check=False)

    if not args.skip_restart:
        print("\nRestart Hermes gateway:")
        if yes("Run sudo systemctl restart hermes-gateway now?", False):
            run(["sudo", "systemctl", "restart", "hermes-gateway"], check=False)
        else:
            print("Run later: sudo systemctl restart hermes-gateway")

    print("\nNext steps")
    print("1. Invite @Hermes to each monitored Slack channel with /invite @Hermes.")
    print("2. In Hermes, run slack_watcher_backfill for configured channels.")
    print("3. Ask: 'resúmeme lo importante de #canal hoy'.")


if __name__ == "__main__":
    main()
