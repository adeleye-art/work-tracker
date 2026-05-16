import subprocess
import sqlite3
import time
import os
import re
from datetime import datetime

from . import config


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    DATETIME,
            app_name     TEXT,
            window_title TEXT,
            project      TEXT,
            is_meeting   INTEGER DEFAULT 0
        )
    """)
    for col_def in ["project TEXT", "is_meeting INTEGER DEFAULT 0"]:
        try:
            conn.execute(f"ALTER TABLE activity ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    return conn


def get_idle_seconds():
    try:
        out = subprocess.check_output(["ioreg", "-c", "IOHIDSystem"], text=True)
        m = re.search(r"HIDIdleTime\s*=\s*(\d+)", out)
        if m:
            return int(m.group(1)) / 1_000_000_000
    except Exception:
        pass
    return 0


def get_active_window():
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
    name = app_name.lower()
    title = window_title.strip()

    if "code" in name and "visual studio" not in name:
        clean = re.sub(r"^[●•]\s*", "", title)
        parts = [p.strip() for p in re.split(r"\s[—–]\s", clean)]
        if len(parts) >= 2:
            return parts[-2] if len(parts) >= 3 else parts[-1]

    if "visual studio" in name:
        parts = [p.strip() for p in title.split(" - ")]
        if parts:
            return parts[0]

    if any(x in name for x in ["rider", "idea", "webstorm", "pycharm", "intellij", "goland"]):
        parts = [p.strip() for p in title.split(" – ")]
        if parts:
            return parts[0]

    if "jupyter" in title.lower():
        parts = [p.strip() for p in title.split(" - ")]
        if parts:
            return parts[0]

    return None


def categorize(app_name, window_title=""):
    n = app_name.lower()
    t = window_title.lower()

    if any(x in n for x in [
        "code", "visual studio", "rider", "idea", "intellij",
        "webstorm", "pycharm", "goland", "xcode",
    ]):
        return "IDE"

    if any(x in n for x in ["teams", "zoom", "webex", "skype"]):
        return "Meeting"

    if "slack" in n:
        return "Meeting" if any(k in t for k in ["huddle", "call", "audio", "video"]) else None

    if "discord" in n:
        return "Meeting" if any(k in t for k in ["voice connected", "screen share", "video call"]) else None

    if any(x in n for x in ["chrome", "firefox", "safari", "edge", "arc", "brave", "opera", "vivaldi"]):
        if any(x in t for x in ["jupyter", "jupyterlab"]):
            return "IDE"
        if any(x in t for x in ["google meet", "meet.google.com", "zoom.us/j", "teams.microsoft.com"]):
            return "Meeting"
        return "Browser"

    if any(x in n for x in ["terminal", "iterm", "warp", "hyper", "kitty", "ghostty"]):
        return "Terminal"

    return None


def main():
    cfg = config.load()
    db_path       = cfg["paths"]["db_path"]
    idle_threshold = cfg["tracker"]["idle_threshold"]
    poll_interval  = cfg["tracker"]["poll_interval"]

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = init_db(db_path)
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Work Tracker started")

    try:
        while True:
            if get_idle_seconds() > idle_threshold:
                time.sleep(poll_interval)
                continue

            app, title = get_active_window()
            if not app:
                time.sleep(poll_interval)
                continue

            cat = categorize(app, title)
            if not cat:
                time.sleep(poll_interval)
                continue

            project = extract_project(app, title)

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
            time.sleep(poll_interval)

    except KeyboardInterrupt:
        conn.close()
        print("Tracker stopped.")


if __name__ == "__main__":
    main()
