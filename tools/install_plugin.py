#!/usr/bin/env python3
"""Install the bundled slack_api watcher plugin into a Hermes checkout."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-root", default="~/.hermes/hermes-agent")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    src_py = repo_root / "plugin" / "slack_api" / "__init__.py"
    src_yaml = repo_root / "plugin" / "slack_api" / "plugin.yaml"
    hermes_root = Path(args.hermes_root).expanduser()
    dest = hermes_root / "plugins" / "slack_api"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_py, dest / "__init__.py")
    shutil.copy2(src_yaml, dest / "plugin.yaml")
    print(f"Installed slack_api watcher plugin to {dest}")
    print("Enable if needed: hermes plugins enable slack-api")


if __name__ == "__main__":
    main()
