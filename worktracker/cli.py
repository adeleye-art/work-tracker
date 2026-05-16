import os
import sys
import subprocess
import sqlite3
from pathlib import Path

import click

from . import config
from . import __version__

PLIST_DIR      = Path.home() / "Library" / "LaunchAgents"
LOGGER_LABEL   = "com.worktracker.logger"
REPORTER_LABEL = "com.worktracker.reporter"
LOGGER_PLIST   = PLIST_DIR / f"{LOGGER_LABEL}.plist"
REPORTER_PLIST = PLIST_DIR / f"{REPORTER_LABEL}.plist"


@click.group()
@click.version_option(__version__, prog_name="worktracker")
def main():
    """Work Tracker — automatic activity tracker with AI-powered daily Excel reports."""
    pass


# ── init ──────────────────────────────────────────────────────────────────────

@main.command()
def init():
    """Interactive setup wizard. Run this once after installing."""
    click.echo("\n" + "─" * 50)
    click.echo("  Welcome to Work Tracker!")
    click.echo("─" * 50 + "\n")

    repos_raw = click.prompt(
        "[1/4] Where are your git repos?\n      (comma-separated paths, e.g. ~/repos, ~/work)",
        default="~/repos",
    )
    repos_list = [r.strip() for r in repos_raw.split(",") if r.strip()]

    reports_dir = click.prompt(
        "\n[2/4] Where should daily reports be saved?",
        default="~/Documents/WorkReports",
    )

    report_hour = click.prompt(
        "\n[3/4] What time to generate the daily report? (24h)",
        default=18,
        type=click.IntRange(0, 23),
    )

    ai_enabled = click.confirm(
        "\n[4/5] Do you want an AI summary in your daily report?\n      (requires Ollama installed — https://ollama.com)",
        default=True,
    )

    model = "llama3.2:3b"
    if ai_enabled:
        installed = _get_ollama_models()
        if installed:
            click.echo("\n      Ollama models found on your machine:")
            for i, m in enumerate(installed, 1):
                click.echo(f"        {i}. {m}")
            click.echo("")
            model = click.prompt(
                "[5/5] Which model should generate the summary?\n      Type a number or the full model name",
                default=installed[0],
            )
            # allow typing "1", "2" etc
            if model.isdigit() and 1 <= int(model) <= len(installed):
                model = installed[int(model) - 1]
        else:
            click.echo("\n      No Ollama models detected. Install one with: ollama pull llama3.2:3b")
            model = click.prompt(
                "[5/5] Model name (or press Enter to use default)",
                default="llama3.2:3b",
            )

    cfg = {
        "paths": {
            "repos_dirs":  repos_list,
            "reports_dir": reports_dir,
            "db_path":     "~/.worktracker/logs.db",
        },
        "tracker": {
            "poll_interval":  10,
            "idle_threshold": 300,
            "report_hour":    report_hour,
        },
        "ai": {
            "ollama_enabled": ai_enabled,
            "ollama_model":   model,
            "ollama_url":     "http://localhost:11434",
        },
    }

    config.save(cfg)

    click.echo(f"\n✅ Config saved → {config.CONFIG_FILE}")

    _install_launchd(report_hour)
    _load_agents()

    click.echo("✅ Background tracker started")
    click.echo(f"✅ Daily reports scheduled at {report_hour:02d}:00 Mon–Fri")
    click.echo(f"✅ Reports will be saved to: {os.path.expanduser(reports_dir)}")
    click.echo("\nYou're all set! Run `worktracker status` to confirm.\n")


# ── start / stop ──────────────────────────────────────────────────────────────

@main.command()
def start():
    """Start the background tracker."""
    if not config.exists():
        click.echo("No config found. Run `worktracker init` first.", err=True)
        raise SystemExit(1)
    _load_agents()
    click.echo("✅ Tracker started.")


@main.command()
def stop():
    """Stop the background tracker."""
    _unload(LOGGER_PLIST,   LOGGER_LABEL,   silent=True)
    _unload(REPORTER_PLIST, REPORTER_LABEL, silent=True)
    click.echo("Tracker stopped.")


# ── report ────────────────────────────────────────────────────────────────────

@main.command()
@click.option("--date", "target_date", default=None,
              help="Date to report on (YYYY-MM-DD). Defaults to today.")
def report(target_date):
    """Generate Excel report for today (or --date YYYY-MM-DD)."""
    from .reporter import generate_report
    path = generate_report(target_date)
    if path:
        subprocess.run(["open", path])


# ── status ────────────────────────────────────────────────────────────────────

@main.command()
def status():
    """Show tracker status and last recorded activity."""
    result = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    running = LOGGER_LABEL in result.stdout

    click.echo(f"Tracker : {'🟢 Running' if running else '🔴 Stopped'}")

    if not config.exists():
        click.echo("Config  : not found — run `worktracker init`")
        return

    click.echo(f"Config  : {config.CONFIG_FILE}")

    db = config.get_db_path()
    if not os.path.exists(db):
        click.echo("Database: no activity recorded yet")
        return

    conn = sqlite3.connect(db)
    c    = conn.cursor()
    c.execute("SELECT timestamp, app_name, project FROM activity ORDER BY timestamp DESC LIMIT 1")
    last = c.fetchone()
    c.execute("SELECT COUNT(*) FROM activity WHERE date(timestamp) = date('now')")
    today_samples = c.fetchone()[0]
    conn.close()

    if last:
        mins = today_samples * 10 // 60
        click.echo(f"Last    : {last[0]}  —  {last[1]}  ({last[2] or 'Unknown project'})")
        click.echo(f"Today   : ~{mins} minutes tracked ({today_samples} samples)")


# ── internal helpers ──────────────────────────────────────────────────────────

def _get_ollama_models() -> list:
    """Return list of locally installed Ollama model names."""
    try:
        r = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5
        )
        lines = r.stdout.strip().splitlines()
        # Skip the header row ("NAME  ID  SIZE  MODIFIED")
        models = [
            line.split()[0] for line in lines[1:]
            if line.strip() and not line.startswith("NAME")
        ]
        return models
    except Exception:
        return []


def _install_launchd(report_hour: int):
    """Write launchd plist files using the current Python interpreter."""
    PLIST_DIR.mkdir(parents=True, exist_ok=True)
    python   = sys.executable
    log_dir  = Path.home() / ".worktracker"
    log_dir.mkdir(parents=True, exist_ok=True)

    LOGGER_PLIST.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{LOGGER_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>worktracker.logger</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>{log_dir}/logger.log</string>
    <key>StandardErrorPath</key><string>{log_dir}/logger.err</string>
</dict>
</plist>'''
    )

    weekday_entries = "\n        ".join(
        f'<dict>'
        f'<key>Weekday</key><integer>{d}</integer>'
        f'<key>Hour</key><integer>{report_hour}</integer>'
        f'<key>Minute</key><integer>0</integer>'
        f'</dict>'
        for d in range(1, 6)
    )

    REPORTER_PLIST.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{REPORTER_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>worktracker.reporter</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        {weekday_entries}
    </array>
    <key>StandardOutPath</key><string>{log_dir}/reporter.log</string>
    <key>StandardErrorPath</key><string>{log_dir}/reporter.err</string>
</dict>
</plist>'''
    )


def _load_agents():
    _unload(LOGGER_PLIST,   LOGGER_LABEL,   silent=True)
    _unload(REPORTER_PLIST, REPORTER_LABEL, silent=True)
    _run(["launchctl", "load", str(LOGGER_PLIST)])
    _run(["launchctl", "load", str(REPORTER_PLIST)])


def _unload(plist: Path, label: str, silent=False):
    if plist.exists():
        _run(["launchctl", "unload", str(plist)], silent=silent)


def _run(cmd, silent=False):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not silent and r.returncode != 0 and r.stderr:
        click.echo(f"Warning: {r.stderr.strip()}", err=True)
