import unittest

from email_extractor.petronect import extrair_tipo_mensagem_cancelada


PREFIX = "foi cancelada pelo seguinte motivo:"
FOOTER = "Essa é uma notificação automática do sistema, favor não respondê-la."


def body_with_banner(reason: str, preheader: str = "resumo truncado") -> str:
    return (
        f"Prezado Fornecedor\n{PREFIX} {preheader}\n"
        "ZjQcmQRYFpfptPreheaderEnd\nZjQcmQRYFpfptBannerStart\n"
        "This Message Is From an External Sender\nReport Suspicious\n"
        "ZjQcmQRYFpfptBannerEnd\nPrezado Fornecedor (usuário)\n"
        f'\" foi cancelada pelo seguinte motivo:\n{reason}\n{FOOTER}\n'
        "Atenciosamente\nServiço de Notificação Petronect"
    )


class CanceladaParserTests(unittest.TestCase):
    def test_normal_reason_uses_fixed_type(self) -> None:
        reason = (
            "Boa tarde, por questão interna este processo será cancelado e postado "
            "em outra oportunidade, desde já agradeço atenção."
        )
        result = extrair_tipo_mensagem_cancelada("Oportunidade Cancelada", body_with_banner(reason))
        self.assertEqual(result.tipo, "Oportunidade Cancelada")
        self.assertEqual(result.mensagem, f"{PREFIX}\n\n{reason}")
        self.assertFalse(result.used_fallback)

    def test_subject_with_surrounding_words_and_case(self) -> None:
        result = extrair_tipo_mensagem_cancelada(
            "[EXTERNAL] OPORTUNIDADE CANCELADA 7001234567", body_with_banner("Motivo")
        )
        self.assertEqual(result.tipo, "Oportunidade Cancelada")

    def test_non_cancelled_subject_is_not_classified(self) -> None:
        result = extrair_tipo_mensagem_cancelada("Oportunidade Prorrogada", body_with_banner("Motivo"))
        self.assertEqual((result.tipo, result.mensagem), ("", ""))

    def test_short_reason_is_not_corrected(self) -> None:
        result = extrair_tipo_mensagem_cancelada("Cancelada", body_with_banner("Refazimento deoportunidade"))
        self.assertEqual(result.mensagem, f"{PREFIX}\n\nRefazimento deoportunidade")

    def test_zero_is_preserved_as_valid_reason(self) -> None:
        result = extrair_tipo_mensagem_cancelada("Cancelada", body_with_banner("0"))
        self.assertEqual(result.mensagem, f"{PREFIX}\n\n0")

    def test_empty_reason_preserves_record_and_prefix(self) -> None:
        result = extrair_tipo_mensagem_cancelada("Cancelada", body_with_banner(""))
        self.assertEqual(result.mensagem, PREFIX)
        self.assertIn("motivo_cancelamento_vazio", result.warnings)

    def test_multiline_reason_preserves_paragraphs(self) -> None:
        reason = "Boa tarde,\n\nO processo será cancelado.\nSerá criada uma nova oportunidade.\n\nObrigado."
        result = extrair_tipo_mensagem_cancelada("Cancelada", body_with_banner(reason))
        self.assertEqual(result.mensagem, f"{PREFIX}\n\n{reason}")

    def test_complete_post_banner_reason_wins_over_truncated_preheader(self) -> None:
        result = extrair_tipo_mensagem_cancelada(
            "Cancelada", body_with_banner("Versão completa do motivo.", "Versão truncada...")
        )
        self.assertNotIn("truncada", result.mensagem)
        self.assertIn("Versão completa do motivo.", result.mensagem)

    def test_fallback_without_banner_uses_last_different_reason_and_warns(self) -> None:
        body = f"{PREFIX}\nPrimeiro\n{FOOTER}\n{PREFIX}\nSegundo\n{FOOTER}"
        result = extrair_tipo_mensagem_cancelada("Cancelada", body)
        self.assertEqual(result.mensagem, f"{PREFIX}\n\nSegundo")
        self.assertTrue(result.used_fallback)
        self.assertTrue(any("múltiplos motivos" in warning for warning in result.warnings))

    def test_missing_automatic_footer_removes_only_safe_footer(self) -> None:
        body = f"ZjQcmQRYFpfptBannerEnd\n{PREFIX}\nMotivo mantido.\nAtenciosamente\nServiço de Notificação Petronect"
        result = extrair_tipo_mensagem_cancelada("Cancelada", body)
        self.assertEqual(result.mensagem, f"{PREFIX}\n\nMotivo mantido.")

    def test_missing_start_preserves_type_and_empty_message(self) -> None:
        result = extrair_tipo_mensagem_cancelada("Cancelada", "Body sem delimitador")
        self.assertEqual(result.tipo, "Oportunidade Cancelada")
        self.assertEqual(result.mensagem, "")


if __name__ == "__main__":
    unittest.main()
