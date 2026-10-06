"""Small shared helpers."""
import random
import time

import config


def pause():
    """Random delay between YouTube Music writes."""
    time.sleep(random.uniform(*config.DELAY_RANGE))


def clean_text(text):
    """YouTube rejects < and > in playlist titles/descriptions."""
    return (text or "").replace("<", "").replace(">", "")


def read_set(path):
    """Read a one-item-per-line memory file into a set (empty if missing)."""
    try:
        with open(path, encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        return set()


def append_line(path, line):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
