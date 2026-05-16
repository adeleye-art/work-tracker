import sqlite3
import requests
import json
import os
from context_scraper import get_git_activity

def generate_daily_report():
    # 1. Connect to the database we built in Step 1
    db_path = os.path.expanduser("~/work-ai/logs.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 2. Get today's logs (last 24 hours)
    c.execute("""
        SELECT app_name, window_title, COUNT(*) as minutes 
        FROM activity 
        WHERE timestamp > datetime('now', '-1 day') 
        GROUP BY app_name, window_title
    """)
    rows = c.fetchall()
    
    if not rows:
        print("No logs found for today. Did you start the logger.py script?")
        return

    # Format the raw app logs for the AI
    app_summary = "\n".join([f"- {row[0]} | {row[1]} | {row[2]} mins" for row in rows])

    # 3. Get the Git context from your WragbyRepos
    git_summary = get_git_activity()

    # 4. Construct the prompt for Ollama
    prompt = f"""
    You are a professional assistant for a Senior Full Stack Engineer. 
    Using the data below, generate a professional daily work timesheet.

    RAW APP LOGS (Time spent in apps):
    {app_summary}

    GIT ACTIVITY (Code changes & commits):
    {git_summary}

    YOUR TASK:
    1. Group the activity by Project/Repo.
    2. Infer the 'Feature Implemented' by matching the 'Modified Files' to the time spent in Rider/VS Code.
    3. Separate 'Development' from 'Sync Meetings' (Teams) and 'Testing' (Chrome).
    4. Provide the report in a clean Markdown table with: | Duration | Project | Activity | Status |

    Be concise and professional.
    """

    # 5. Call Ollama (using llama3.2:3b which you have installed)
    print("🤖 AI is analyzing your day... please wait.")
    try:
        response = requests.post('http://localhost:11434/api/generate', 
                                 json={
                                     'model': 'llama3.2:3b', 
                                     'prompt': prompt, 
                                     'stream': False
                                 })
        result = response.json()
        print("\n--- ✅ YOUR DAILY TIMESHEET REPORT ---")
        print(result['response'])
    except Exception as e:
        print(f"Error calling Ollama: {e}")

if __name__ == "__main__":
    generate_daily_report()