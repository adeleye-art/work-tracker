import os
import subprocess
from datetime import date as _date

from . import config


def get_git_activity(active_projects=None, target_date=None):
    """
    Returns a formatted string of commits made on target_date.

    active_projects: set of project names from the activity tracker.
                     When given, only matching repos are shown.
    target_date:     ISO date string (YYYY-MM-DD). Defaults to today.
    """
    if target_date is None:
        target_date = _date.today().isoformat()

    filter_names = (
        {p.lower() for p in active_projects if p and p != "Unknown"}
        if active_projects else None
    )

    activity_report = []

    # Support multiple repo root directories from config
    for repos_root in config.get_repos_dirs():
        repos_root = os.path.expanduser(repos_root)
        if not os.path.isdir(repos_root):
            continue

        try:
            find_cmd = f"find {repos_root} -maxdepth 3 -name .git -type d -prune"
            repos = subprocess.check_output(find_cmd, shell=True, text=True).splitlines()
        except subprocess.CalledProcessError:
            continue

        for dot_git in repos:
            repo_path = os.path.dirname(dot_git)
            repo_name = os.path.basename(repo_path)

            if filter_names is not None and repo_name.lower() not in filter_names:
                continue

            try:
                cmd = (
                    f"git -C {repo_path} log "
                    f"--since='{target_date} 00:00:00' "
                    f"--until='{target_date} 23:59:59' "
                    f"--oneline"
                )
                commits = subprocess.check_output(cmd, shell=True, text=True).strip()
            except subprocess.CalledProcessError:
                continue

            if commits:
                activity_report.append(f"### REPO: {repo_name}\nCommits:\n{commits}\n")

    return (
        "\n".join(activity_report)
        if activity_report
        else "No commits made to tracked projects today."
    )
