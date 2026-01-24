from __future__ import annotations

from backupctl.constants import MONTH_NAMES, WEEKDAY_NAMES


def _format_time(minute: str, hour: str) -> str:
    if minute == "*" and hour == "*":
        return "every minute"
    if hour == "*" and minute != "*":
        return f"every hour at minute {minute}"
    if minute == "*" and hour != "*":
        return f"every minute during hour {hour}"
    if minute.isdigit() and hour.isdigit():
        return f"at {hour.zfill(2)}:{minute.zfill(2)}"
    return f"at hour {hour} minute {minute}"


def _human_field(label: str, value: str) -> str:
    if value == "*":
        return "any"
    if label == "weekday" and value in WEEKDAY_NAMES:
        return WEEKDAY_NAMES[value]
    if label == "month" and value in MONTH_NAMES:
        return MONTH_NAMES[value]
    return value


def human_schedule_from_cron(command: str) -> str:
    parts = command.split()
    if len(parts) < 6:
        return "unknown"
    minute, hour, day, month, weekday = parts[:5]
    time_phrase = _format_time(minute, hour)

    if day == "*" and month == "*" and weekday == "*":
        return f"Every day {time_phrase}"
    if weekday != "*" and day == "*" and month == "*":
        return f"Every {_human_field('weekday', weekday)} {time_phrase}"
    if day != "*" and month == "*":
        return f"Every month on day {_human_field('day', day)} {time_phrase}"
    if day != "*" and month != "*":
        return (
            f"Every year on {_human_field('month', month)} "
            f"{_human_field('day', day)} {time_phrase}"
        )
    if day == "*" and month != "*":
        return f"Every year in {_human_field('month', month)} {time_phrase}"

    return ", ".join(
        [
            f"minute={_human_field('minute', minute)}",
            f"hour={_human_field('hour', hour)}",
            f"day={_human_field('day', day)}",
            f"month={_human_field('month', month)}",
            f"weekday={_human_field('weekday', weekday)}",
        ]
    )
