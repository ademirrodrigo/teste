import unittest

from bpo_app.nfse_client import (
    NFSeClientConfig,
    NFSeConfigurationError,
    _normalize_address,
)


class NFSeClientUnitTest(unittest.TestCase):
    def test_normalizes_relative_service_address(self) -> None:
        result = _normalize_address("https://nfse.exemplo.gov.br/nfse?wsdl", "nfse.asmx")
        self.assertEqual(result, "https://nfse.exemplo.gov.br/nfse.asmx")

    def test_config_normalizes_relative_service_url(self) -> None:
        config = NFSeClientConfig(
            wsdl_url="https://nfse.exemplo.gov.br/nfse?wsdl",
            service_url="nfse.asmx",
        )
        self.assertEqual(config.service_url, "https://nfse.exemplo.gov.br/nfse.asmx")

    def test_raises_for_missing_address(self) -> None:
        with self.assertRaises(NFSeConfigurationError):
            _normalize_address("https://nfse.exemplo.gov.br/nfse?wsdl", "   ")


if __name__ == "__main__":
    unittest.main()
