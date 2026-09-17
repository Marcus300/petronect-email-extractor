import unittest

from email_extractor.models import (
    SUBJECT_OPTIONS,
    sender_is_allowed,
    subject_matches,
    subject_terms,
)


class FilterModelTests(unittest.TestCase):
    def test_visible_options_do_not_expose_search_terms(self) -> None:
        self.assertEqual(
            SUBJECT_OPTIONS,
            (
                "Sala",
                "Nova Oportunidade",
                "Chamado",
                "Cancelada",
                "Prorrogada",
                "Pedido",
                "Relatório",
            ),
        )
        self.assertTrue(all("(" not in option and ")" not in option for option in SUBJECT_OPTIONS))

    def test_chamado_combines_all_requested_terms(self) -> None:
        self.assertEqual(
            subject_terms("Chamado"),
            ("Atenção ao Chamado", "ticket", "chamado"),
        )
        self.assertTrue(subject_matches("Novo ticket disponível", "Chamado"))
        self.assertTrue(subject_matches("ATENÇÃO AO CHAMADO 7001234567", "Chamado"))

    def test_option_with_multiple_terms_matches_either_term(self) -> None:
        self.assertTrue(subject_matches("Criação de Oportunidade 7001234567", "Nova Oportunidade"))
        self.assertTrue(subject_matches("Oportunidade Publicada", "Nova Oportunidade"))
        self.assertFalse(subject_matches("Oportunidade Cancelada", "Nova Oportunidade"))

    def test_blank_and_free_text_behavior_is_preserved(self) -> None:
        self.assertTrue(subject_matches("Qualquer assunto", ""))
        self.assertTrue(subject_matches("Aviso personalizado", "personalizado"))

    def test_only_configured_senders_are_allowed(self) -> None:
        self.assertTrue(sender_is_allowed("ordersender-prod@ansmtp.ariba.com"))
        self.assertTrue(sender_is_allowed("PETRONECT@PETRONECT.COM.BR"))
        self.assertFalse(sender_is_allowed("outro@example.com"))


if __name__ == "__main__":
    unittest.main()
