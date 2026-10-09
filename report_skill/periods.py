"""Turn "today", "2026-10-09", "last week" into concrete [start, end) windows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional


@dataclass
class Period:
    kind: str  # "daily" | "weekly" | "custom"
    start: datetime
    end: datetime
    first_day: date
    last_day: date

    @property
    def days(self):
        d = self.first_day
        while d <= self.last_day:
            yield d
            d += timedelta(days=1)


def _local(d: date, hour: int) -> datetime:
    return datetime.combine(d, time(hour)).astimezone()


def logical_today(day_start_hour: int, now: Optional[datetime] = None) -> date:
    now = now or datetime.now().astimezone()
    return (now - timedelta(hours=day_start_hour)).date()


def parse_day(value: Optional[str], day_start_hour: int) -> date:
    today = logical_today(day_start_hour)
    if not value or value in ("today", "今天"):
        return today
    if value in ("yesterday", "昨天"):
        return today - timedelta(days=1)
    if value.lstrip("-").isdigit():  # "-1" = yesterday
        return today + timedelta(days=int(value))
    return date.fromisoformat(value)


def daily(value: Optional[str], day_start_hour: int = 4) -> Period:
    d = parse_day(value, day_start_hour)
    return Period("daily", _local(d, day_start_hour), _local(d + timedelta(days=1), day_start_hour), d, d)


def weekly(value: Optional[str], day_start_hour: int = 4) -> Period:
    """value: None/"this" (current week), "last", or any date inside the wanted week."""
    today = logical_today(day_start_hour)
    if value in (None, "", "this", "本周"):
        anchor = today
    elif value in ("last", "上周"):
        anchor = today - timedelta(days=7)
    else:
        anchor = parse_day(value, day_start_hour)
    monday = anchor - timedelta(days=anchor.weekday())
    sunday = monday + timedelta(days=6)
    return Period("weekly", _local(monday, day_start_hour), _local(sunday + timedelta(days=1), day_start_hour),
                  monday, sunday)


def custom(since: str, until: Optional[str], day_start_hour: int = 4) -> Period:
    first = parse_day(since, day_start_hour)
    last = parse_day(until, day_start_hour) if until else logical_today(day_start_hour)
    return Period("custom", _local(first, day_start_hour), _local(last + timedelta(days=1), day_start_hour),
                  first, last)
