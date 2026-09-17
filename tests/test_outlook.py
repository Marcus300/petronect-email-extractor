import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from email_extractor.outlook import OutlookEmailSource
from email_extractor.models import SearchCriteria


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

    @patch("email_extractor.outlook.locale.getlocale", return_value=("pt_BR", "cp1252"))
    def test_ambiguous_text_date_uses_day_month_for_brazilian_locale(self, _locale) -> None:
        self.assertEqual(
            OutlookEmailSource._coerce_datetime("09/10/2026 10:30:00"),
            datetime(2026, 10, 9, 10, 30),
        )

    @patch("email_extractor.outlook.locale.getlocale", return_value=("en_US", "cp1252"))
    def test_ambiguous_text_date_uses_month_day_for_us_locale(self, _locale) -> None:
        self.assertEqual(
            OutlookEmailSource._coerce_datetime("09/10/2026 10:30:00"),
            datetime(2026, 9, 10, 10, 30),
        )

    @patch("email_extractor.outlook.locale.getlocale", return_value=("en_US", "cp1252"))
    def test_unambiguous_text_date_does_not_depend_on_locale(self, _locale) -> None:
        self.assertEqual(
            OutlookEmailSource._coerce_datetime("16/09/2026 10:30:00"),
            datetime(2026, 9, 16, 10, 30),
        )

    def test_structural_sample_does_not_include_subject_or_body_content(self) -> None:
        attachments = type("Attachments", (), {"Count": 2})()
        message = type(
            "Message",
            (),
            {
                "Subject": "conteúdo confidencial do assunto",
                "Body": "conteúdo confidencial do corpo",
                "HTMLBody": "<p>conteúdo confidencial</p>",
                "MessageClass": "IPM.Note",
                "Attachments": attachments,
                "Size": 1234,
            },
        )()
        sample = OutlookEmailSource._structural_sample(
            message,
            1,
            datetime(2026, 9, 16, 10, 30),
            datetime(2026, 9, 16, 10, 30),
        )
        self.assertIn("assunto_caracteres=32", sample)
        self.assertIn("body_caracteres=30", sample)
        self.assertIn("anexos=2", sample)
        self.assertNotIn("confidencial", sample)

    def test_sender_email_reads_standard_smtp_property(self) -> None:
        message = type(
            "Message", (), {"SenderEmailAddress": "petronect@petronect.com.br"}
        )()
        self.assertEqual(
            OutlookEmailSource._sender_email(message),
            "petronect@petronect.com.br",
        )

    def test_purchase_order_pipeline_uses_outlook_received_time_and_original_subject(self) -> None:
        body = (
            "De:\nCliente\nRECAP\nPedido de compra\n(Novo)\n4515588132\n"
            "Valor:\n$\n2.160,67\nUSD\nVersão: 1\n"
            "Número do contrato\n4600676634"
        )
        message = type(
            "Message",
            (),
            {
                "MessageClass": "IPM.Note",
                "ReceivedTime": datetime(2026, 9, 17, 11, 30),
                "SenderEmailAddress": "ordersender-prod@ansmtp.ariba.com",
                "Subject": "[EXTERNAL] Novo PEDIDO 4515588132",
                "Body": body,
            },
        )()

        class Items:
            Count = 1

            @staticmethod
            def Item(_index):
                return message

            @staticmethod
            def Sort(_field, _descending):
                return None

        folder = type(
            "Folder",
            (),
            {
                "FolderPath": r"\\Caixa\Inbox",
                "Items": Items(),
                "Folders": type("Folders", (), {"Count": 0})(),
            },
        )()
        criteria = SearchCriteria(
            "Caixa",
            r"\\Caixa\Inbox",
            datetime(2026, 9, 17, 10, 0),
            "Pedido",
            Path("pedidos.xlsx"),
        )
        source = object.__new__(OutlookEmailSource)
        records = list(source._walk_folder(folder, criteria, None, None, None))

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].received_at, datetime(2026, 9, 17, 11, 30))
        self.assertEqual(records[0].subject, "[EXTERNAL] Novo PEDIDO 4515588132")
        self.assertEqual(records[0].pedido, "4515588132")
        self.assertEqual(records[0].valor_total, Decimal("2160.67"))
        self.assertEqual(records[0].email_id, "")
