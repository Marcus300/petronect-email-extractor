import unittest

from email_extractor.models import (
    SUBJECT_OPTIONS,
    sender_is_allowed,
    structured_subject_category,
    subject_matches,
    subject_terms,
    uses_structured_layout,
)


class FilterModelTests(unittest.TestCase):
    def test_visible_options_include_combined_label_and_remain_sorted(self) -> None:
        self.assertEqual(
            SUBJECT_OPTIONS,
            (
                "0.Conjunto (Sala, Prorrogação, Cancelamento)",
                "Cancelada",
                "Chamado",
                "Nova Oportunidade",
                "Pedido",
                "Prorrogada",
                "Relatório",
                "Sala",
            ),
        )
        self.assertEqual(len(SUBJECT_OPTIONS), len(set(SUBJECT_OPTIONS)))

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

    def test_prorrogada_matches_any_subject_containing_the_category_word(self) -> None:
        self.assertTrue(subject_matches("Prorrogada", "Prorrogada"))
        self.assertTrue(subject_matches("OPORTUNIDADE PRORROGADA 7001234567", "Prorrogada"))
        self.assertTrue(subject_matches("[EXTERNAL] prorrogada", "Prorrogada"))

    def test_cancelada_matches_any_subject_containing_the_category_word(self) -> None:
        self.assertTrue(subject_matches("Cancelada", "Cancelada"))
        self.assertTrue(subject_matches("OPORTUNIDADE CANCELADA 7001234567", "Cancelada"))
        self.assertTrue(subject_matches("[EXTERNAL] oportunidade cancelada", "Cancelada"))

    def test_combined_option_matches_three_terms_with_one_filter(self) -> None:
        combined = "0.Conjunto (Sala, Prorrogação, Cancelamento)"
        self.assertEqual(subject_terms(combined), ("sala", "prorrogada", "cancelada"))
        self.assertTrue(subject_matches("[EXTERNAL] SALA 7001234567", combined))
        self.assertTrue(subject_matches("Oportunidade Prorrogada", combined))
        self.assertTrue(subject_matches("Oportunidade Cancelada", combined))
        self.assertFalse(subject_matches("Relatório Divulgado", combined))
        self.assertTrue(uses_structured_layout(combined))

    def test_combined_option_routes_each_subject_to_its_individual_parser(self) -> None:
        combined = "0.Conjunto (Sala, Prorrogação, Cancelamento)"
        self.assertEqual(structured_subject_category("Nova SALA", combined), "sala")
        self.assertEqual(structured_subject_category("Oportunidade PRORROGADA", combined), "prorrogada")
        self.assertEqual(structured_subject_category("Oportunidade cancelada", combined), "cancelada")
        self.assertEqual(structured_subject_category("Outro assunto", combined), "")
        self.assertEqual(
            structured_subject_category("Sala cancelada", combined),
            "cancelada",
        )

    def test_blank_and_free_text_behavior_is_preserved(self) -> None:
        self.assertTrue(subject_matches("Qualquer assunto", ""))
        self.assertTrue(subject_matches("Aviso personalizado", "personalizado"))

    def test_only_configured_senders_are_allowed(self) -> None:
        self.assertTrue(sender_is_allowed("ordersender-prod@ansmtp.ariba.com"))
        self.assertTrue(sender_is_allowed("PETRONECT@PETRONECT.COM.BR"))
        self.assertFalse(sender_is_allowed("outro@example.com"))


if __name__ == "__main__":
    unittest.main()
