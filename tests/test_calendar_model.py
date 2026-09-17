import unittest
from datetime import date

from email_extractor.calendar_model import (
    CALENDAR_DAY_PALETTE,
    WEEKDAY_NAMES_SUNDAY_FIRST,
    day_state,
    month_title,
    month_weeks,
    shift_month,
)


class CalendarModelTests(unittest.TestCase):
    def test_week_starts_on_sunday_in_pt_br(self) -> None:
        self.assertEqual(
            WEEKDAY_NAMES_SUNDAY_FIRST,
            ("Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"),
        )

    def test_all_month_names_are_deterministically_pt_br(self) -> None:
        expected = (
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        )
        self.assertEqual(tuple(month_title(2026, month).split()[0] for month in range(1, 13)), expected)
        self.assertEqual(month_title(2026, 9), "Setembro 2026")

    def test_first_day_position_uses_sunday_first_logic(self) -> None:
        # 01/09/2026 is a Tuesday, therefore column 2 when Sunday is column 0.
        weeks = month_weeks(2026, 9)
        self.assertEqual(weeks[0][2], 1)

    def test_previous_next_and_year_transitions(self) -> None:
        self.assertEqual(shift_month(2026, 9, -1), (2026, 8))
        self.assertEqual(shift_month(2026, 9, 1), (2026, 10))
        self.assertEqual(shift_month(2026, 12, 1), (2027, 1))
        self.assertEqual(shift_month(2027, 1, -1), (2026, 12))
        self.assertEqual(month_title(*shift_month(2026, 12, 1)), "Janeiro 2027")

    def test_today_and_selected_have_distinct_states(self) -> None:
        today = date(2026, 9, 17)
        selected = date(2026, 9, 21)
        self.assertEqual(day_state(today, today, selected), "today")
        self.assertEqual(day_state(selected, today, selected), "selected")
        self.assertEqual(day_state(today, today, today), "today_selected")

    def test_normal_date_has_normal_state(self) -> None:
        self.assertEqual(
            day_state(date(2026, 9, 10), date(2026, 9, 17), date(2026, 9, 21)),
            "normal",
        )

    def test_palette_has_distinct_high_contrast_states(self) -> None:
        self.assertEqual(set(CALENDAR_DAY_PALETTE), {"normal", "today", "selected", "today_selected"})
        self.assertEqual(CALENDAR_DAY_PALETTE["normal"]["background"], "#FFFFFF")
        self.assertEqual(CALENDAR_DAY_PALETTE["today"]["background"], "#DDF4FF")
        self.assertEqual(CALENDAR_DAY_PALETTE["selected"]["background"], "#0969DA")
        self.assertEqual(CALENDAR_DAY_PALETTE["today_selected"]["background"], "#0550AE")
