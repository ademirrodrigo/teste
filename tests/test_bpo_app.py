import os
import shutil
import tempfile
import unittest
from datetime import date, timedelta
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


if __name__ == "__main__":
    unittest.main()
