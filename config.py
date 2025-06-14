import os
import json

CONFIG_FILE = "config.json" 

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

def validate_base_dir(base_dir: str) -> bool:
    """Check if base_dir exists and is writable."""
    return os.path.isdir(base_dir) and os.access(base_dir, os.W_OK)
