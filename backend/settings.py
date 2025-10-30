import json
import os
import stat
from typing import Any

SETTINGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SETTINGS_PATH = os.path.join(SETTINGS_DIR, "settings.json")


DEFAULT_SETTINGS: dict[str, Any] = {
    "openai_api_key": None,
    "openai_model": "gpt-4o-mini",
    "provider": "openai",
    "auto_execute": False,
    "region": "auto",
    "theme": "minimal",
}


def _ensure_settings_file() -> None:
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    if not os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "w") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)
        # Restrict permissions to user read/write only
        os.chmod(SETTINGS_PATH, stat.S_IRUSR | stat.S_IWUSR)


def get_settings() -> dict[str, Any]:
    """Load application settings from disk and env overrides."""
    _ensure_settings_file()
    try:
        with open(SETTINGS_PATH) as f:
            settings = json.load(f)
    except Exception:
        settings = DEFAULT_SETTINGS.copy()

    # Environment variable overrides
    if os.getenv("OPENAI_API_KEY"):
        settings["openai_api_key"] = os.getenv("OPENAI_API_KEY")
    if os.getenv("OPENAI_MODEL"):
        settings["openai_model"] = os.getenv("OPENAI_MODEL")

    # Do not return secrets in plaintext to callers by default
    return settings


def update_settings(partial: dict[str, Any]) -> dict[str, Any]:
    """Update settings on disk. Returns the saved object."""
    _ensure_settings_file()
    with open(SETTINGS_PATH) as f:
        current = json.load(f)

    current.update({k: v for k, v in partial.items() if k in DEFAULT_SETTINGS})

    with open(SETTINGS_PATH, "w") as f:
        json.dump(current, f, indent=2)

    return current
