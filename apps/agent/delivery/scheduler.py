from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError


FALLBACK_TIMEZONES = {
    "UTC": timezone.utc,
    "Etc/UTC": timezone.utc,
    "Asia/Singapore": timezone(timedelta(hours=8), name="Asia/Singapore"),
    "Asia/Shanghai": timezone(timedelta(hours=8), name="Asia/Shanghai"),
}


@dataclass(frozen=True)
class DailyBriefSchedule:
    timezone_name: str = "Asia/Singapore"
    delivery_hour: int = 7
    delivery_minute: int = 5

    def zone(self) -> ZoneInfo:
        if not 0 <= self.delivery_hour <= 23:
            raise ValueError("delivery_hour must be between 0 and 23.")
        if not 0 <= self.delivery_minute <= 59:
            raise ValueError("delivery_minute must be between 0 and 59.")
        try:
            return ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError:
            if self.timezone_name in FALLBACK_TIMEZONES:
                return FALLBACK_TIMEZONES[self.timezone_name]
            raise ValueError(f"Unknown timezone_name: {self.timezone_name}")


def compute_next_scheduled_run(*, now_utc: str, schedule: DailyBriefSchedule) -> str:
    zone = schedule.zone()
    current_utc = _parse_utc_iso(now_utc)
    current_local = current_utc.astimezone(zone)
    next_local = current_local.replace(
        hour=schedule.delivery_hour,
        minute=schedule.delivery_minute,
        second=0,
        microsecond=0,
    )
    if current_local >= next_local:
        next_local = next_local + timedelta(days=1)
    return _utc_iso(next_local.astimezone(timezone.utc))


def scheduled_local_date(*, generated_at_utc: str, schedule: DailyBriefSchedule) -> str:
    zone = schedule.zone()
    current_utc = _parse_utc_iso(generated_at_utc)
    return current_utc.astimezone(zone).date().isoformat()


def _parse_utc_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
