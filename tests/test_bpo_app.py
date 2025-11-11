import os
import shutil
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

os.environ.setdefault("BPO_SECRET_KEY", "test-secret-key")
os.environ.setdefault("BPO_ADMIN_EMAIL", "admin@test.example")
os.environ.setdefault("BPO_ADMIN_PASSWORD", "SenhaForte!123")
os.environ.setdefault("BPO_ADMIN_NAME", "Administrador Teste")

from fastapi.testclient import TestClient  # noqa: E402

from bpo_app import database, main  # noqa: E402


class BPOAppFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="bpo_test_")
        self.db_path = Path(self.temp_dir) / "test.db"
        database.init_engine(f"sqlite:///{self.db_path}")
        self.client_ctx = TestClient(main.app)
        self.client = self.client_ctx.__enter__()

    def tearDown(self) -> None:
        self.client_ctx.__exit__(None, None, None)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def auth_headers(self) -> dict[str, str]:
        response = self.client.post(
            "/auth/login",
            json={
                "email": os.environ["BPO_ADMIN_EMAIL"],
                "password": os.environ["BPO_ADMIN_PASSWORD"],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_login_accepts_uppercase_email(self) -> None:
        response = self.client.post(
            "/auth/login",
            json={
                "email": os.environ["BPO_ADMIN_EMAIL"].upper(),
                "password": os.environ["BPO_ADMIN_PASSWORD"],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_login_with_invalid_email_format_returns_unauthorized(self) -> None:
        response = self.client.post(
            "/auth/login",
            json={"email": "usuario", "password": os.environ["BPO_ADMIN_PASSWORD"]},
        )
        self.assertEqual(response.status_code, 401, response.text)

    def test_admin_password_sync_from_env(self) -> None:
        email = os.environ["BPO_ADMIN_EMAIL"]
        original_password = os.environ["BPO_ADMIN_PASSWORD"]
        response = self.client.post(
            "/auth/login",
            json={"email": email, "password": original_password},
        )
        self.assertEqual(response.status_code, 200, response.text)

        new_password = "NovaSenha!456"
        main.settings.admin_password = new_password
        main.settings.admin_password_from_env = True
        try:
            main.on_startup()
            updated_login = self.client.post(
                "/auth/login",
                json={"email": email, "password": new_password},
            )
            self.assertEqual(updated_login.status_code, 200, updated_login.text)

            old_password_login = self.client.post(
                "/auth/login",
                json={"email": email, "password": original_password},
            )
            self.assertEqual(old_password_login.status_code, 401, old_password_login.text)
        finally:
            main.settings.admin_password = original_password
            main.settings.admin_password_from_env = True
            main.on_startup()

    def test_startup_creates_admin_for_new_email(self) -> None:
        original_email = main.settings.admin_email
        original_password = main.settings.admin_password
        original_password_from_env = main.settings.admin_password_from_env

        new_email = "novo-admin@test.example"
        new_password = "SenhaNova!789"

        main.settings.admin_email = new_email
        main.settings.admin_password = new_password
        main.settings.admin_password_from_env = True

        try:
            main.on_startup()

            response = self.client.post(
                "/auth/login",
                json={"email": new_email, "password": new_password},
            )
            self.assertEqual(response.status_code, 200, response.text)
        finally:
            main.settings.admin_email = original_email
            main.settings.admin_password = original_password
            main.settings.admin_password_from_env = original_password_from_env
            main.on_startup()

    def test_end_to_end_flow(self) -> None:
        headers = self.auth_headers()

        company_payload = {
            "name": "Empresa Teste Ltda",
            "trade_name": "Empresa Teste",
            "document": "12345678000199",
            "notes": "Cliente piloto",
        }
        company_resp = self.client.post("/companies", json=company_payload, headers=headers)
        self.assertEqual(company_resp.status_code, 200, company_resp.text)
        company_id = company_resp.json()["id"]

        account_payload = {
            "company_id": company_id,
            "name": "Conta Principal",
            "bank_name": "Banco Teste",
            "account_number": "1234-5",
            "initial_balance": 1000.0,
        }
        account_resp = self.client.post("/bank-accounts", json=account_payload, headers=headers)
        self.assertEqual(account_resp.status_code, 200, account_resp.text)
        account_id = account_resp.json()["id"]

        transaction_payload = {
            "company_id": company_id,
            "bank_account_id": account_id,
            "date": date.today().isoformat(),
            "description": "Recebimento de venda",
            "amount": 2500.0,
            "transaction_type": "inflow",
        }
        txn_resp = self.client.post("/transactions", json=transaction_payload, headers=headers)
        self.assertEqual(txn_resp.status_code, 200, txn_resp.text)
        txn_data = txn_resp.json()
        self.assertTrue(txn_data["auto_classified"])

        csv_content = "data,descricao,valor,tipo\n" "2024-01-05,Pagamento fornecedor,1500,saida\n"
        files = {"file": ("extrato.csv", csv_content, "text/csv")}
        import_resp = self.client.post(
            f"/transactions/import?company_id={company_id}",
            headers=headers,
            files=files,
        )
        self.assertEqual(import_resp.status_code, 200, import_resp.text)
        summary = import_resp.json()
        self.assertEqual(summary["imported"], summary["total_records"])

        list_resp = self.client.get(f"/transactions?company_id={company_id}", headers=headers)
        self.assertEqual(list_resp.status_code, 200, list_resp.text)
        transactions = list_resp.json()
        self.assertGreaterEqual(len(transactions), 2)

        start_date = (date.today().replace(day=1) - timedelta(days=30)).isoformat()
        end_date = date.today().isoformat()
        report_resp = self.client.get(
            f"/reports/financial-health?company_id={company_id}&start_date={start_date}&end_date={end_date}",
            headers=headers,
        )
        self.assertEqual(report_resp.status_code, 200, report_resp.text)
        report_data = report_resp.json()
        self.assertIn("cash_flow", report_data)
        self.assertIn("dre", report_data)

        export_xlsx = self.client.get(
            f"/reports/export?company_id={company_id}&start_date={start_date}&end_date={end_date}&export_format=xlsx",
            headers=headers,
        )
        self.assertEqual(export_xlsx.status_code, 200, export_xlsx.text)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            export_xlsx.headers.get("content-type", ""),
        )

        export_pdf = self.client.get(
            f"/reports/export?company_id={company_id}&start_date={start_date}&end_date={end_date}&export_format=pdf",
            headers=headers,
        )
        self.assertEqual(export_pdf.status_code, 200, export_pdf.text)
        self.assertIn("application/pdf", export_pdf.headers.get("content-type", ""))

        dashboard_resp = self.client.get("/dashboard/overview", headers=headers)
        self.assertEqual(dashboard_resp.status_code, 200, dashboard_resp.text)
        highlights = dashboard_resp.json()
        self.assertTrue(any(item["title"] for item in highlights))

    def test_nfse_route_uses_stubbed_client(self) -> None:
        headers = self.auth_headers()

        calls: list[tuple[str, str, str]] = []

        class StubClient:
            async def call_operation(self, operation: str, cabec: str, dados: str) -> str:
                calls.append((operation, cabec, dados))
                return "<xml-retorno />"

        original_resolver = main.resolve_nfse_client

        def fake_resolver(config, use_cache: bool = True):
            self.assertEqual(config.wsdl_url, "http://nfse.example/wsdl")
            self.assertEqual(config.service_url, "http://nfse.example/nfse.asmx")
            return StubClient()

        main.resolve_nfse_client = fake_resolver  # type: ignore[assignment]
        try:
            response = self.client.post(
                "/integrations/nfse/ConsultarNfsePorRps",
                headers=headers,
                json={
                    "nfse_cabec_msg": "<cabecalho />",
                    "nfse_dados_msg": "<dados />",
                    "wsdl_url": "http://nfse.example/wsdl",
                    "service_url": "http://nfse.example/nfse.asmx",
                },
            )
        finally:
            main.resolve_nfse_client = original_resolver  # type: ignore[assignment]

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["output_xml"], "<xml-retorno />")
        self.assertEqual(calls[0][0], "ConsultarNfsePorRps")

    def test_goiania_nfse_emission_endpoint_builds_payload(self) -> None:
        headers = self.auth_headers()

        captured: dict[str, str] = {}

        class StubClient:
            async def call_operation(self, operation: str, cabec: str, dados: str) -> str:
                captured["operation"] = operation
                captured["cabecalho"] = cabec
                captured["dados"] = dados
                return "<nfse-retorno />"

        original_resolver = main.resolve_nfse_client

        def fake_resolver(config, use_cache: bool = True):
            self.assertEqual(config.wsdl_url, "http://nfse.example/wsdl")
            self.assertEqual(config.service_url, "http://nfse.example/nfse.asmx")
            return StubClient()

        main.resolve_nfse_client = fake_resolver  # type: ignore[assignment]
        try:
            response = self.client.post(
                "/integrations/nfse/goiania/emissao",
                headers=headers,
                json={
                    "numero_lote": "20240001",
                    "numero_rps": "15",
                    "serie_rps": "GO",
                    "tipo_rps": 1,
                    "data_emissao": datetime(2024, 1, 10, 10, 30, 0).isoformat(),
                    "natureza_operacao": 1,
                    "regime_especial_tributacao": 6,
                    "optante_simples": 1,
                    "incentivador_cultural": 2,
                    "status_rps": 1,
                    "prestador": {
                        "cnpj": "12.345.678/0001-99",
                        "inscricao_municipal": "123456",
                    },
                    "servico": {
                        "item_lista_servico": "0701",
                        "codigo_tributacao_municipio": "070199",
                        "discriminacao": "Serviço de gestão financeira mensal",
                        "valores": {
                            "valor_servicos": "1500.00",
                            "iss_retido": 2,
                        },
                    },
                    "tomador": {
                        "razao_social": "Cliente NFSe Teste LTDA",
                        "cpf_cnpj": "00.987.654/3210-00",
                        "email": "cliente@teste.com",
                        "telefone": "62999990000",
                        "endereco": {
                            "logradouro": "Rua Central",
                            "numero": "100",
                            "bairro": "Centro",
                            "codigo_municipio": "5208707",
                            "uf": "GO",
                            "cep": "74000000",
                        },
                    },
                    "wsdl_url": "http://nfse.example/wsdl",
                    "service_url": "http://nfse.example/nfse.asmx",
                },
            )
        finally:
            main.resolve_nfse_client = original_resolver  # type: ignore[assignment]

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["output_xml"], "<nfse-retorno />")
        self.assertEqual(captured.get("operation"), "GerarNfse")
        self.assertIn("GerarNfseEnvio", captured.get("dados", ""))
        self.assertIn("<Numero>15</Numero>", captured.get("dados", ""))
        self.assertIn("<RazaoSocial>Cliente NFSe Teste LTDA</RazaoSocial>", captured.get("dados", ""))


if __name__ == "__main__":
    unittest.main()
