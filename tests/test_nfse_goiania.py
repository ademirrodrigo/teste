import unittest
from datetime import datetime
from decimal import Decimal

from bpo_app.nfse_goiania import (
    GoianiaNfseEmission,
    GoianiaPrestador,
    GoianiaServico,
    GoianiaServicoValores,
    GoianiaTomador,
    GoianiaTomadorEndereco,
    build_goiania_payload,
)


class GoianiaNFSeBuilderTest(unittest.TestCase):
    def test_payload_contains_core_elements(self) -> None:
        emission = GoianiaNfseEmission(
            numero_lote="20240001",
            numero_rps="15",
            serie_rps="GO",
            tipo_rps=1,
            data_emissao=datetime(2024, 1, 10, 10, 30, 0),
            natureza_operacao=1,
            regime_especial_tributacao=6,
            optante_simples=1,
            incentivador_cultural=2,
            status_rps=1,
            prestador=GoianiaPrestador(cnpj="12.345.678/0001-99", inscricao_municipal="123456"),
            servico=GoianiaServico(
                valores=GoianiaServicoValores(valor_servicos=Decimal("1500.00")),
                item_lista_servico="0701",
                codigo_tributacao_municipio="070199",
                discriminacao="Serviço de gestão financeira mensal",
            ),
            tomador=GoianiaTomador(
                razao_social="Cliente NFSe Teste LTDA",
                cpf_cnpj="00.987.654/3210-00",
                inscricao_municipal=None,
                email="cliente@teste.com",
                telefone="62999990000",
                endereco=GoianiaTomadorEndereco(
                    logradouro="Rua Central",
                    numero="100",
                    bairro="Centro",
                    cep="74000000",
                ),
            ),
        )

        cabecalho, dados = build_goiania_payload(emission)

        self.assertIn("<VersaoDados>2.03</VersaoDados>", cabecalho)
        self.assertIn("GerarNfseEnvio", dados)
        self.assertIn("<Numero>15</Numero>", dados)
        self.assertIn("<Cnpj>12345678000199</Cnpj>", dados)
        self.assertIn("<CodigoMunicipio>5208707</CodigoMunicipio>", dados)
        self.assertIn("<RazaoSocial>Cliente NFSe Teste LTDA</RazaoSocial>", dados)


if __name__ == "__main__":
    unittest.main()
