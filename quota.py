"""Tracks official-API quota across runs, so re-running the same day is safe."""
import datetime
import json
from pathlib import Path

import config


class QuotaStop(Exception):
    """Raised when today's quota budget is used up."""


def quota_day():
    """Current date in Pacific time, which is when YouTube's quota resets."""
    try:
        from zoneinfo import ZoneInfo
        now = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
    except Exception:  # no timezone database available (pip install tzdata)
        now = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=8)
    return now.date().isoformat()


class QuotaTracker:
    def __init__(self, path=None, budget=None, today=quota_day):
        self.path = Path(path or config.QUOTA_FILE)
        self.budget = budget if budget is not None else config.DAILY_QUOTA_BUDGET
        self._today = today
        self.used = self._load()

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("day") == self._today():
                return int(data.get("used", 0))
        except Exception:
            pass
        return 0

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"day": self._today(), "used": self.used}), encoding="utf-8")

    @property
    def remaining(self):
        return max(0, self.budget - self.used)

    def require(self, units):
        if self.used + units > self.budget:
            raise QuotaStop()

    def spend(self, units):
        self.used += units
        self._save()
