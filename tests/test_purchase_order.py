import unittest
from decimal import Decimal

from email_extractor.purchase_order import extrair_pedido_compra


def order_body(
    order="4515588132",
    status="Novo",
    values=("2.160,67 USD",),
    version="1",
    client="RECAP",
    contract="4600676634",
    banner=True,
):
    value_lines = "\n".join(
        f"Valor:\n$\n{pair.split()[0]}\n{pair.split()[1]}" for pair in values
    )
    content = (
        f"De:\nCliente\n{client}\nRUA Endereço que não pertence ao cliente\n"
        f"Pedido de compra\n({status})\n{order}\n{value_lines}\nVersão: {version}\n"
        f"Número da linha do contrato\n10\nNúmero do contrato\n{contract}\n"
        "Subtotal:\n999.999,99\nBRL"
    )
    if banner:
        return (
            "Pedido de compra\n(Novo)\n4599999999\nValor:\n$\n1,00\nUSD\nVersão: 9\n"
            "ZjQcmQRYFpfptBannerEnd\n" + content
        )
    return content


class PurchaseOrderParserTests(unittest.TestCase):
    def test_new_usd_order(self) -> None:
        result = extrair_pedido_compra("Novo PEDIDO 4515588132", order_body())
        self.assertTrue(result.valid)
        self.assertEqual(result.pedido, "4515588132")
        self.assertEqual(result.contrato, "4600676634")
        self.assertEqual(result.cliente, "RECAP")
        self.assertEqual(result.status, "Novo")
        self.assertEqual(result.versao, "1")
        self.assertEqual(result.valor_total, Decimal("2160.67"))
        self.assertEqual(result.moeda, "USD")

    def test_new_brl_order_preserves_magnitude(self) -> None:
        result = extrair_pedido_compra(
            "PEDIDO 4515581420",
            order_body("4515581420", values=("184.790,47 BRL",)),
        )
        self.assertEqual(result.valor_total, Decimal("184790.47"))
        self.assertEqual(result.moeda, "BRL")

    def test_altered_order_uses_last_complete_value_before_version(self) -> None:
        result = extrair_pedido_compra(
            "ORDER 4515466768",
            order_body(
                "4515466768",
                "Alterado",
                ("12.482,00 USD", "10.318,86 USD"),
                "3",
            ),
        )
        self.assertEqual(result.status, "Alterado")
        self.assertEqual(result.valor_total, Decimal("10318.86"))
        self.assertEqual(result.moeda, "USD")
        self.assertEqual(result.versao, "3")

    def test_dynamic_status_removes_url_and_image_noise(self) -> None:
        result = extrair_pedido_compra(
            "PEDIDO 4515588132",
            order_body(status="https://service.ariba.com/asn_compare_arrow.gif\nParcialmente recebido"),
        )
        self.assertEqual(result.status, "Parcialmente recebido")

    def test_composed_client_uses_only_first_useful_line(self) -> None:
        for client in ("RECAP", "REFAP", "REPAR", "JV 220 - BÚZIOS"):
            with self.subTest(client=client):
                result = extrair_pedido_compra(
                    "PEDIDO 4515588132", order_body(client=client)
                )
                self.assertEqual(result.cliente, client)
                self.assertNotIn("RUA", result.cliente)

    def test_subject_has_priority_and_divergence_is_reported(self) -> None:
        result = extrair_pedido_compra(
            "PEDIDO 4511111111", order_body(order="4522222222")
        )
        self.assertEqual(result.pedido, "4511111111")
        self.assertIn("pedido_subject_body_divergente", result.warnings)

    def test_order_falls_back_only_to_main_block(self) -> None:
        result = extrair_pedido_compra("Novo pedido", order_body(order="4515588132"))
        self.assertEqual(result.pedido, "4515588132")
        self.assertIn("pedido_obtido_por_fallback_do_body", result.warnings)

    def test_ambiguous_subject_falls_back_to_single_order_in_main_block(self) -> None:
        result = extrair_pedido_compra(
            "PEDIDO 4511111111 substitui 4522222222",
            order_body(order="4533333333"),
        )
        self.assertEqual(result.pedido, "4533333333")
        self.assertIn("pedido_subject_ambiguo", result.warnings)

    def test_repeated_same_formal_contract_is_accepted(self) -> None:
        body = order_body() + "\nNúmero do contrato\n4600676634"
        result = extrair_pedido_compra("PEDIDO 4515588132", body)
        self.assertEqual(result.contrato, "4600676634")

    def test_different_formal_contracts_are_not_chosen_silently(self) -> None:
        body = order_body() + "\nNúmero do contrato\n4600000001"
        result = extrair_pedido_compra("PEDIDO 4515588132", body)
        self.assertEqual(result.contrato, "")
        self.assertIn("pedido_multiplos_contratos_formais", result.warnings)

    def test_missing_header_value_does_not_use_subtotal(self) -> None:
        body = order_body(values=()).replace("Versão: 1", "Versão: 1\nSubtotal:\n1.238.748,44\nBRL")
        result = extrair_pedido_compra("PEDIDO 4515588132", body)
        self.assertIsNone(result.valor_total)
        self.assertEqual(result.moeda, "")
        self.assertIn("pedido_valor_moeda_nao_identificados", result.warnings)

    def test_missing_banner_uses_audited_fallback(self) -> None:
        result = extrair_pedido_compra("PEDIDO 4515588132", order_body(banner=False))
        self.assertTrue(result.used_fallback)
        self.assertTrue(any("fallback" in warning for warning in result.warnings))

    def test_body_without_purchase_order_block_is_rejected(self) -> None:
        result = extrair_pedido_compra("PEDIDO 4515588132", "Texto comum de sala")
        self.assertFalse(result.valid)
        self.assertIn("pedido_bloco_principal_nao_identificado", result.warnings)


if __name__ == "__main__":
    unittest.main()
