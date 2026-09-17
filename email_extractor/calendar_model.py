"""Testable calendar calculations independent from Tk and the Windows locale."""

import calendar
from datetime import date

from .localization import MONTH_NAMES_PT_BR, WEEKDAY_NAMES_SUNDAY_FIRST


CALENDAR_DAY_PALETTE = {
    "normal": {
        "background": "#FFFFFF",
        "foreground": "#24292F",
        "border": "#D0D7DE",
        "active_background": "#F6F8FA",
    },
    "today": {
        "background": "#DDF4FF",
        "foreground": "#0969DA",
        "border": "#54AEFF",
        "active_background": "#B6E3FF",
    },
    "selected": {
        "background": "#0969DA",
        "foreground": "#FFFFFF",
        "border": "#0550AE",
        "active_background": "#033D8B",
    },
    "today_selected": {
        "background": "#0550AE",
        "foreground": "#FFFFFF",
        "border": "#54AEFF",
        "active_background": "#033D8B",
    },
}


def month_title(year: int, month: int) -> str:
    return f"{MONTH_NAMES_PT_BR[month]} {year}"


def shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    absolute = year * 12 + month - 1 + offset
    return absolute // 12, absolute % 12 + 1


def month_weeks(year: int, month: int) -> list[list[int]]:
    """Return a Sunday-first matrix where zero represents an empty cell."""
    return calendar.Calendar(firstweekday=calendar.SUNDAY).monthdayscalendar(year, month)


def day_state(day: date, today: date, selected: date) -> str:
    if day == today == selected:
        return "today_selected"
    if day == today:
        return "today"
    if day == selected:
        return "selected"
    return "normal"


__all__ = [
    "CALENDAR_DAY_PALETTE",
    "WEEKDAY_NAMES_SUNDAY_FIRST",
    "day_state",
    "month_title",
    "month_weeks",
    "shift_month",
]
