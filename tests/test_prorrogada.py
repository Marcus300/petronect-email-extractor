import unittest

from email_extractor.petronect import extrair_tipo_mensagem_prorrogada


EXPECTED_TYPE = "Prorrogação de Oportunidade"


def body_with_banner(final_date: str = "18.09.2026", final_time: str = "17:00:00") -> str:
    return (
        "Prezado cliente Empresa Confidencial CNPJ 00.000.000/0001-00\n"
        "A oportunidade ID 7001234567 teve no dia 17.09.2026 10:04:00 seu tempo prorrogado.\n"
        "Nova data final: truncada\n"
        "ZjQcmQRYFpfptPreheaderEnd\n"
        "ZjQcmQRYFpfptBannerStart\n"
        "This Message Is From an External Sender Proofpoint URLDefense Report Suspicious\n"
        "ZjQcmQRYFpfptBannerEnd\n"
        "Prezado cliente Empresa Confidencial<br>"
        "A oportunidade ID 7001234567 teve no dia 17.09.2026 10:04:00, seu tempo "
        "para envio de proposta prorrogado.<br />"
        f"Nova data final: “{final_date}, {final_time}” (Horário de Brasília). "
        "Caso ainda não tenha enviado sua proposta, você tem até a nova data.<br/>"
        "Para efetuar sua cotação acesse https://www.petronect.com.br\n"
        "Atenciosamente Serviço de Notificação Petronect"
    )


class ProrrogadaParserTests(unittest.TestCase):
    def assert_result(self, subject: str, body: str, expected_message: str) -> None:
        result = extrair_tipo_mensagem_prorrogada(subject, body)
        self.assertEqual(result.tipo, EXPECTED_TYPE)
        self.assertEqual(result.mensagem, expected_message)

    def test_exact_subject(self) -> None:
        self.assert_result(
            "Prorrogada",
            body_with_banner(),
            "Nova data final: “18.09.2026, 17:00:00” (Horário de Brasília)",
        )

    def test_subject_with_surrounding_words_and_different_case(self) -> None:
        self.assert_result(
            "[EXTERNAL] OPORTUNIDADE PRORROGADA 7001234567",
            body_with_banner("21.09.2026"),
            "Nova data final: “21.09.2026, 17:00:00” (Horário de Brasília)",
        )

    def test_variable_time_is_preserved(self) -> None:
        self.assert_result(
            "oportunidade prorrogada",
            body_with_banner("22.09.2026", "20:00:00"),
            "Nova data final: “22.09.2026, 20:00:00” (Horário de Brasília)",
        )

    def test_preheader_and_alteration_date_are_ignored(self) -> None:
        result = extrair_tipo_mensagem_prorrogada("Prorrogada", body_with_banner())
        self.assertNotIn("17.09.2026 10:04:00", result.mensagem)
        self.assertNotIn("truncada", result.mensagem)

    def test_message_contains_only_the_required_segment(self) -> None:
        result = extrair_tipo_mensagem_prorrogada("Prorrogada", body_with_banner())
        forbidden = (
            "Empresa Confidencial", "CNPJ", "7001234567", "17.09.2026", "ZjQcm",
            "External Sender", "Proofpoint", "URLDefense", "Report Suspicious",
            "Caso ainda não", "Para efetuar", "petronect.com.br", "Serviço de Notificação",
        )
        for value in forbidden:
            self.assertNotIn(value, result.mensagem)

    def test_fallback_without_banner_uses_single_complete_occurrence(self) -> None:
        body = 'Texto inicial\nNova data final: "23.09.2026, 08:30:45" (Horário de Brasília). Depois'
        result = extrair_tipo_mensagem_prorrogada("Prorrogada", body)
        self.assertEqual(
            result.mensagem,
            "Nova data final: “23.09.2026, 08:30:45” (Horário de Brasília)",
        )
        self.assertTrue(result.used_fallback)

    def test_fallback_repeated_same_value_uses_value_normally(self) -> None:
        occurrence = 'Nova data final: “24.09.2026, 09:15:00” (Horário de Brasília)'
        result = extrair_tipo_mensagem_prorrogada("Prorrogada", f"{occurrence}\n{occurrence}")
        self.assertEqual(result.mensagem, occurrence)
        self.assertFalse(any("diferentes" in warning for warning in result.warnings))

    def test_fallback_with_different_values_uses_last_and_warns(self) -> None:
        result = extrair_tipo_mensagem_prorrogada(
            "Prorrogada",
            "Nova data final: “24.09.2026, 09:15:00” (Horário de Brasília)\n"
            "Nova data final: “25.09.2026, 10:30:00” (Horário de Brasília)",
        )
        self.assertEqual(
            result.mensagem,
            "Nova data final: “25.09.2026, 10:30:00” (Horário de Brasília)",
        )
        self.assertTrue(any("diferentes" in warning for warning in result.warnings))

    def test_missing_complete_value_preserves_type_and_empty_message(self) -> None:
        result = extrair_tipo_mensagem_prorrogada(
            "Prorrogada", "Nova data final: incompleta e sem valor"
        )
        self.assertEqual(result.tipo, EXPECTED_TYPE)
        self.assertEqual(result.mensagem, "")
        self.assertTrue(any("não identificada" in warning for warning in result.warnings))

    def test_banner_prevents_using_complete_preheader_value(self) -> None:
        result = extrair_tipo_mensagem_prorrogada(
            "Prorrogada",
            "Nova data final: “26.09.2026, 11:00:00” (Horário de Brasília)\n"
            "ZjQcmQRYFpfptBannerEnd\nNotificação real incompleta",
        )
        self.assertEqual(result.tipo, EXPECTED_TYPE)
        self.assertEqual(result.mensagem, "")

    def test_non_prorrogada_subject_is_not_classified(self) -> None:
        result = extrair_tipo_mensagem_prorrogada("Oportunidade Publicada", body_with_banner())
        self.assertEqual(result.tipo, "")
        self.assertEqual(result.mensagem, "")


if __name__ == "__main__":
    unittest.main()
