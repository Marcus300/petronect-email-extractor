import unittest

from email_extractor.petronect import extrair_tipo_mensagem


class PetronectParserTests(unittest.TestCase):
    def test_simple_message(self) -> None:
        result = extrair_tipo_mensagem(
            'ZjQcmQRYFpfptBannerEnd\n'
            'Informamos que existe uma nova mensagem para o assunto "Folha de dados" '
            'na sala de colaboração\n'
            '"Boa tarde!\nFoi enviado uma Folha de dados, não atende?"\n'
            'Para acessar a oportunidade clique aqui'
        )
        self.assertEqual(result.tipo, "Folha de dados")
        self.assertEqual(result.mensagem, "Boa tarde!\nFoi enviado uma Folha de dados, não atende?")

    def test_internal_quotes_are_preserved(self) -> None:
        result = extrair_tipo_mensagem(
            'Informamos que existe uma nova mensagem para o assunto "Dados" na sala de colaboração\n'
            '"Para propostas idêntico "não" é necessário..."\nPara acessar a oportunidade'
        )
        self.assertIn('"não"', result.mensagem)

    def test_long_message_and_automatic_footer(self) -> None:
        body = (
            'ZjQcmQRYFpfptBannerEnd\n'
            'Informamos que existe uma nova mensagem para o assunto '
            '"Circular 1 – Convite para Participação em Oportunidades – Petronect" '
            'na sala de colaboração\n'
            '"Circular 1 – Convite para Participação em Oportunidades – Petronect\n'
            'RC:36463170\nOP: 7004634270\nITEM:3\n'
            'Atenciosamente,\nBPO Level"\n'
            'Para acessar a oportunidade\n'
            'Atenciosamente,\nServiço de Notificação Petronect.'
        )
        result = extrair_tipo_mensagem(body)
        self.assertEqual(result.tipo, "Circular 1 – Convite para Participação em Oportunidades – Petronect")
        self.assertTrue(result.mensagem.endswith("Atenciosamente,\nBPO Level"))
        self.assertNotIn("Para acessar a oportunidade", result.mensagem)
        self.assertIn("RC:36463170\nOP: 7004634270\nITEM:3", result.mensagem)

    def test_com_anexos_is_not_part_of_type(self) -> None:
        result = extrair_tipo_mensagem(
            'Informamos que existe uma nova mensagem (COM ANEXOS) para o assunto '
            '"Documentos (Livre de inspeção)" na sala de colaboração\n'
            '"Mensagem"\nPara acessar a oportunidade'
        )
        self.assertEqual(result.tipo, "Documentos (Livre de inspeção)")

    def test_duplicate_outer_quotes_are_removed(self) -> None:
        result = extrair_tipo_mensagem(
            'Informamos que existe uma nova mensagem para o assunto "Aviso" na sala de colaboração\n'
            '""Prezados,\nLevel""\nPara acessar a oportunidade'
        )
        self.assertEqual(result.mensagem, "Prezados,\nLevel")


if __name__ == "__main__":
    unittest.main()
