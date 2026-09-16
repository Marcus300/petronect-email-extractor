import unittest

from email_extractor.cleaning import clean_body, find_email_id


class CleaningTests(unittest.TestCase):
    def test_clean_body_removes_html_and_extra_spaces(self) -> None:
        self.assertEqual(
            clean_body("<p> Pedido 7001234567 </p><br>\n\nDetalhe"),
            "Pedido 7001234567\nDetalhe",
        )


    def test_find_email_id_requires_ten_digits_starting_with_700(self) -> None:
        self.assertEqual(find_email_id("referência 7001234567"), "7001234567")
        self.assertEqual(find_email_id("referência 6001234567"), "")


if __name__ == "__main__":
    unittest.main()