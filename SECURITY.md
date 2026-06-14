# Security

Do not publish:

- Slack bot tokens (`xoxb-...`)
- Slack app tokens (`xapp-...`)
- Hermes `.env`
- SQLite watcher databases
- local channel/user IDs if they are sensitive in your environment

The included scripts are intended to configure a local Hermes installation. Review generated `.env` changes before restarting Hermes.

For issues, open a GitHub issue without including secrets.
