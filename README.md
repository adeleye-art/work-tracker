# Work Tracker

> Automatic work activity tracker for macOS — tracks your IDEs, meetings, and browser usage all day, then drops a polished Excel report on your desk at 6 PM with an AI-written summary of your day.

[![PyPI version](https://img.shields.io/pypi/v/devtrackr)](https://pypi.org/project/devtrackr/)
[![Python](https://img.shields.io/pypi/pyversions/devtrackr)](https://pypi.org/project/devtrackr/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/adeleyealarape)

---

## What it does

- **Tracks time** in VS Code, Rider, IntelliJ, Visual Studio, Jupyter, Xcode and more
- **Detects meetings** in Teams, Zoom, Webex, Skype, Google Meet, Slack huddles
- **Knows which project** you're in by reading the IDE window title
- **Skips idle time** — if you step away, it stops counting
- **Reads your git commits** and links them to the project you worked on
- **Generates a daily Excel report** at a time you choose (default 6 PM, Mon–Fri)
- **AI narrative summary** via a local Ollama model — 100% private, no cloud

---

## Requirements

- macOS (uses AppleScript and launchd)
- Python 3.9+
- [Ollama](https://ollama.com/) installed locally (optional, for AI summary)

---

## Install

```bash
pip install devtrackr
```

---

## Quick start

```bash
worktracker init
```

That's it. The wizard asks four questions, then installs and starts the tracker automatically.

```
──────────────────────────────────────────────────
  Welcome to Work Tracker!
──────────────────────────────────────────────────

[1/4] Where are your git repos? (comma-separated paths)
      > ~/repos, ~/work/client-projects

[2/4] Where should daily reports be saved?
      > ~/Documents/WorkReports

[3/4] What time to generate the daily report? (24h)
      > 18

[4/4] Ollama model for AI summary?
      > llama3.2:3b

✅ Config saved → ~/.worktracker/config.toml
✅ Background tracker started
✅ Daily reports scheduled at 18:00 Mon–Fri
✅ Reports will be saved to: ~/Documents/WorkReports
```

---

## Commands

| Command | Description |
|---|---|
| `worktracker init` | First-time setup wizard |
| `worktracker status` | Show running status and last recorded activity |
| `worktracker report` | Generate today's report right now |
| `worktracker report --date 2026-05-15` | Generate report for a specific date |
| `worktracker start` | Start the background tracker |
| `worktracker stop` | Stop the background tracker |

---

## Excel report

Each daily report contains four sheets:

| Sheet | Contents |
|---|---|
| **Summary** | Total hours, meeting hours, coding hours; per-app/project breakdown |
| **By Project** | Hours per project sorted by time spent |
| **Git Activity** | Commits you made today, per repo |
| **AI Summary** | A 3–5 sentence narrative of your day written by Ollama |

---

## Configuration

Config lives at `~/.worktracker/config.toml`. Edit it any time:

```toml
[paths]
repos_dirs  = ["~/repos", "~/work"]   # scan multiple repo roots
reports_dir = "~/Documents/WorkReports"
db_path     = "~/.worktracker/logs.db"

[tracker]
poll_interval  = 10    # seconds between samples
idle_threshold = 300   # seconds idle before pausing
report_hour    = 18    # 24h — report fires Mon–Fri at this hour

[ai]
ollama_enabled = true
ollama_model   = "llama3.2:3b"
ollama_url     = "http://localhost:11434"
```

After editing, restart the tracker:

```bash
worktracker stop && worktracker start
```

---

## Apps tracked

**IDEs** — VS Code, Visual Studio, Rider, IntelliJ IDEA, PyCharm, WebStorm, GoLand, Xcode, Jupyter (in browser)

**Meetings** — Microsoft Teams, Zoom, Webex, Skype, Google Meet, Slack (huddles), Discord (voice channels)

**Browsers** — Chrome, Firefox, Safari, Edge, Arc, Brave, Opera, Vivaldi

**Terminal** — Terminal, iTerm2, Warp, Hyper, Kitty, Ghostty

---

## Privacy

Everything stays on your Mac:
- Activity data → `~/.worktracker/logs.db` (SQLite, only you can read it)
- Reports → your chosen folder
- AI summary → processed by Ollama running locally, nothing sent to the cloud

---

## Contributing

Pull requests are welcome! Please open an issue first to discuss what you'd like to change.

```bash
git clone https://github.com/adeleye-art/devtrackr
cd devtrackr
pip install -e .
worktracker init
```

---

## ❤️ Support this project

Work Tracker is free and open source. If it saves you time, consider buying me a coffee — it helps me keep working on it!

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/adeleyealarape)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-%E2%9D%A4-%23db61a2.svg?style=for-the-badge&logo=GitHub&logoColor=white)](https://github.com/sponsors/adeleyealarape)

---

## License

[GNU GPL v3](LICENSE) © 2026 Adeleye Alarape
