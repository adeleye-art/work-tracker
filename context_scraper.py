import os
import subprocess
from datetime import date

# CONFIG: Set this to the folder where you keep your projects
PROJECTS_DIR = os.path.expanduser("~/WragbyRepos")

def get_git_activity(active_projects=None, target_date=None):
    """
    Finds git repos and extracts commits for target_date only.

    active_projects: optional set/list of project names from the activity tracker.
    When provided, only repos whose folder name matches an active project are shown.
    """
    if target_date is None:
        target_date = date.today().isoformat()

    activity_report = []

    try:
        find_cmd = f"find {PROJECTS_DIR} -maxdepth 3 -name .git -type d -prune"
        repos = subprocess.check_output(find_cmd, shell=True, text=True).splitlines()
    except subprocess.CalledProcessError:
        return "Could not find project directories."

    # Normalise for case-insensitive matching
    filter_names = (
        {p.lower() for p in active_projects if p and p != "Unknown"}
        if active_projects else None
    )

    for dot_git in repos:
        repo_path = os.path.dirname(dot_git)
        repo_name = os.path.basename(repo_path)

        # Skip repos the user wasn't tracked working on today
        if filter_names is not None and repo_name.lower() not in filter_names:
            continue

        try:
            commit_cmd = f"git -C {repo_path} log --since='{target_date} 00:00:00' --until='{target_date} 23:59:59' --oneline"
            commits = subprocess.check_output(commit_cmd, shell=True, text=True).strip()
        except subprocess.CalledProcessError:
            continue

        if commits:
            report = f"### REPO: {repo_name}\n"
            report += f"Commits Today:\n{commits}\n"
            activity_report.append(report)

    return "\n".join(activity_report) if activity_report else "No commits made to tracked projects today."

if __name__ == "__main__":
    print("🔍 Scanning projects for today's activity...")
    print(get_git_activity())