import os
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

CONFIG_DIR  = Path.home() / ".worktracker"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULTS = {
    "paths": {
        "repos_dirs":  ["~/repos"],
        "reports_dir": "~/Documents/WorkReports",
        "db_path":     "~/.worktracker/logs.db",
    },
    "tracker": {
        "poll_interval":   10,
        "idle_threshold":  300,
        "report_hour":     18,
    },
    "ai": {
        "ollama_enabled": True,
        "ollama_model":   "llama3.2:3b",
        "ollama_url":     "http://localhost:11434",
    },
}


def exists():
    return CONFIG_FILE.exists()


def load():
    """Return config as a dict with all ~ paths expanded."""
    if not CONFIG_FILE.exists():
        return _expand(DEFAULTS)

    if tomllib is None:
        raise RuntimeError(
            "Missing TOML library. Run: pip install tomli"
        )

    with open(CONFIG_FILE, "rb") as f:
        on_disk = tomllib.load(f)

    return _expand(_deep_merge(DEFAULTS, on_disk))


def save(cfg: dict):
    """Write cfg dict to ~/.worktracker/config.toml."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    for section, values in cfg.items():
        lines.append(f"[{section}]")
        for key, val in values.items():
            if isinstance(val, list):
                items = ", ".join(f'"{v}"' for v in val)
                lines.append(f"{key} = [{items}]")
            elif isinstance(val, bool):
                lines.append(f"{key} = {'true' if val else 'false'}")
            elif isinstance(val, str):
                lines.append(f'{key} = "{val}"')
            else:
                lines.append(f"{key} = {val}")
        lines.append("")
    CONFIG_FILE.write_text("\n".join(lines))


def get_db_path() -> str:
    return load()["paths"]["db_path"]


def get_reports_dir() -> str:
    return load()["paths"]["reports_dir"]


def get_repos_dirs() -> list:
    return load()["paths"]["repos_dirs"]


# ── internals ─────────────────────────────────────────────────────────────────

def _expand(cfg: dict) -> dict:
    result = {}
    for section, values in cfg.items():
        result[section] = {}
        for key, val in values.items():
            if isinstance(val, str):
                result[section][key] = os.path.expanduser(val)
            elif isinstance(val, list):
                result[section][key] = [
                    os.path.expanduser(v) if isinstance(v, str) else v
                    for v in val
                ]
            else:
                result[section][key] = val
    return result


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result
