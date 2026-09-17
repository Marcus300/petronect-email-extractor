import unittest

from email_extractor.localization import unique_sorted


class LocalizationTests(unittest.TestCase):
    def test_sort_is_case_and_accent_insensitive_and_removes_duplicates(self) -> None:
        self.assertEqual(
            unique_sorted(("Sala", "árvore", "Cancelada", "Árvore", "pedido", "Chamado")),
            ("árvore", "Cancelada", "Chamado", "pedido", "Sala"),
        )


if __name__ == "__main__":
    unittest.main()
