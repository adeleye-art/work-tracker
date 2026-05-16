import subprocess
import sqlite3
import time
import os
import re
from datetime import datetime

DB_PATH = os.path.expanduser("~/work-ai/logs.db")
IDLE_THRESHOLD = 300  # seconds of system idle before we stop counting
POLL_INTERVAL = 10    # seconds between samples


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   DATETIME,
            app_name    TEXT,
            window_title TEXT,
            project     TEXT,
            is_meeting  INTEGER DEFAULT 0
        )
    """)
    # Non-destructive migration for existing DBs
    for col_def in ["project TEXT", "is_meeting INTEGER DEFAULT 0"]:
        try:
            conn.execute(f"ALTER TABLE activity ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    return conn


def get_idle_seconds():
    """Returns macOS system idle time in seconds via IOKit."""
    try:
        out = subprocess.check_output(["ioreg", "-c", "IOHIDSystem"], text=True)
        m = re.search(r"HIDIdleTime\s*=\s*(\d+)", out)
        if m:
            return int(m.group(1)) / 1_000_000_000
    except Exception:
        pass
    return 0


def get_active_window():
    """Returns (app_name, window_title) of the frontmost application."""
    script = '''
tell application "System Events"
    set frontApp to first process whose frontmost is true
    set appName to name of frontApp
    set winTitle to ""
    tell frontApp
        try
            set winTitle to name of front window
        end try
        if winTitle is "" then
            try
                set winTitle to value of attribute "AXTitle" of front window
            end try
        end if
    end tell
    return appName & "||" & winTitle
end tell'''
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5
        )
        out = r.stdout.strip()
        if "||" in out:
            app, title = out.split("||", 1)
            return app.strip(), title.strip()
        return out.strip(), ""
    except Exception:
        return "", ""


def check_teams_in_meeting():
    """Checks all Teams windows (even in background) for meeting indicators."""
    script = '''
tell application "System Events"
    if not (exists process "Microsoft Teams") then return ""
    try
        set wins to name of every window of process "Microsoft Teams"
        return wins as string
    on error
        return ""
    end try
end tell'''
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5
        )
        titles = r.stdout.lower()
        return any(k in titles for k in ["meeting", "call", "connected", "| "])
    except Exception:
        return False


def extract_project(app_name, window_title):
    """
    Parse project/workspace name from window title.

    VS Code titles:  "● file.ts — ProjectFolder — Visual Studio Code"
    Rider titles:    "ProjectName – src/File.cs – JetBrains Rider 2024.x"
    """
    name = app_name.lower()
    title = window_title.strip()

    # VS Code: "● file.ts — ProjectFolder — Visual Studio Code"
    if "code" in name and "visual studio" not in name:
        clean = re.sub(r"^[●•]\s*", "", title)
        parts = [p.strip() for p in re.split(r"\s[—–]\s", clean)]
        if len(parts) >= 2:
            return parts[-2] if len(parts) >= 3 else parts[-1]

    # Visual Studio: "ProjectName - Microsoft Visual Studio"
    if "visual studio" in name:
        parts = [p.strip() for p in title.split(" - ")]
        if parts:
            return parts[0]

    # JetBrains IDEs: "ProjectName – src/File.cs – JetBrains Rider 2024.x"
    if any(x in name for x in ["rider", "idea", "webstorm", "pycharm", "intellij", "goland"]):
        parts = [p.strip() for p in title.split(" – ")]
        if parts:
            return parts[0]

    # Jupyter in browser: "notebook.ipynb - Jupyter Notebook" or "JupyterLab"
    t_lower = title.lower()
    if "jupyter" in t_lower:
        parts = [p.strip() for p in title.split(" - ")]
        if parts:
            return parts[0]  # notebook filename as project

    return None


def categorize(app_name, window_title=""):
    """Returns tracking category or None if this app should be ignored."""
    n = app_name.lower()
    t = window_title.lower()

    # IDEs (native apps)
    if any(x in n for x in [
        "code",                              # VS Code
        "visual studio",                     # Visual Studio (Mac/Parallels)
        "rider",                             # JetBrains Rider
        "idea", "intellij",                  # IntelliJ IDEA
        "webstorm", "pycharm", "goland",     # other JetBrains
        "xcode",                             # Xcode
    ]):
        return "IDE"

    # Standalone meeting apps
    if any(x in n for x in ["teams", "zoom", "webex", "skype"]):
        return "Meeting"

    # Slack — only count as meeting when in a huddle/call
    if "slack" in n:
        return "Meeting" if any(k in t for k in ["huddle", "call", "audio", "video"]) else None

    # Discord — only count when in a voice/video channel
    if "discord" in n:
        return "Meeting" if any(k in t for k in ["voice connected", "screen share", "video call"]) else None

    # Browsers — detect Jupyter and web-based meetings from window title
    if any(x in n for x in ["chrome", "firefox", "safari", "edge", "arc", "brave", "opera", "vivaldi"]):
        if any(x in t for x in ["jupyter", "jupyterlab"]):
            return "IDE"   # Jupyter Notebook running in browser
        if any(x in t for x in ["google meet", "meet.google.com", "zoom.us/j", "teams.microsoft.com"]):
            return "Meeting"
        return "Browser"

    if any(x in n for x in ["terminal", "iterm", "warp", "hyper", "kitty", "ghostty"]):
        return "Terminal"

    return None


def main():
    conn = init_db()
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Work Tracker started")

    try:
        while True:
            if get_idle_seconds() > IDLE_THRESHOLD:
                time.sleep(POLL_INTERVAL)
                continue

            app, title = get_active_window()
            if not app:
                time.sleep(POLL_INTERVAL)
                continue

            cat = categorize(app, title)
            if not cat:
                time.sleep(POLL_INTERVAL)
                continue

            project = extract_project(app, title)

            # All meeting-category apps are meetings except Teams,
            # which is also used for chat — needs explicit check.
            is_meeting = 0
            if cat == "Meeting":
                if "teams" in app.lower():
                    in_meeting = any(k in title.lower() for k in ["meeting", "call", "connected"])
                    if not in_meeting:
                        in_meeting = check_teams_in_meeting()
                    is_meeting = 1 if in_meeting else 0
                else:
                    is_meeting = 1

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO activity (timestamp, app_name, window_title, project, is_meeting)"
                " VALUES (?, ?, ?, ?, ?)",
                (now, app, title, project, is_meeting)
            )
            conn.commit()
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        conn.close()
        print("Tracker stopped.")


if __name__ == "__main__":
    main()
