import unittest
from datetime import datetime

from email_extractor.outlook import OutlookEmailSource


class MissingReceivedTime:
    @property
    def ReceivedTime(self):
        raise RuntimeError("ReceivedTime indisponível")


class PropertyAccessorMessage:
    @property
    def ReceivedTime(self):
        raise RuntimeError("ReceivedTime indisponível")

    class PropertyAccessor:
        @staticmethod
        def GetProperty(_property_tag):
            return datetime(2026, 9, 16, 10, 30)


class OutlookTests(unittest.TestCase):
    def test_missing_received_time_is_ignored(self) -> None:
        self.assertIsNone(OutlookEmailSource._received_at(MissingReceivedTime()))

    def test_received_time_is_converted_to_naive_datetime(self) -> None:
        message = type("Message", (), {"ReceivedTime": datetime(2026, 9, 16, 10, 30)})()
        self.assertEqual(
            OutlookEmailSource._received_at(message),
            datetime(2026, 9, 16, 10, 30),
        )

    def test_received_time_uses_mapi_fallback(self) -> None:
        self.assertEqual(
            OutlookEmailSource._received_at(PropertyAccessorMessage()),
            datetime(2026, 9, 16, 10, 30),
        )

    def test_coerce_datetime_handles_com_like_value(self) -> None:
        value = type(
            "ComDate",
            (),
            {
                "year": 2026,
                "month": 9,
                "day": 16,
                "hour": 10,
                "minute": 30,
                "second": 5,
                "microsecond": 123000,
            },
        )()
        self.assertEqual(
            OutlookEmailSource._coerce_datetime(value),
            datetime(2026, 9, 16, 10, 30, 5, 123000),
        )